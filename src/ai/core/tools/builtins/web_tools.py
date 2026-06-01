"""网络工具 — 网页获取和搜索。"""

import ipaddress
import json
import logging
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urlparse

from langchain_core.tools import tool

from src.ai.core.tools.register import register_tool

logger = logging.getLogger(__name__)

# 内网 IP 范围 — 阻止 SSRF 攻击
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


class _HTMLTextExtractor(HTMLParser):
    """轻量 HTML 文本提取器，丢弃 script/style 标签内容。"""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False
        self._skip_tags = {"script", "style", "noscript"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._skip_tags:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in self._skip_tags:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def _html_to_text(html: str) -> str:
    """从 HTML 中提取纯文本。"""
    extractor = _HTMLTextExtractor()
    extractor.feed(html)
    text = extractor.get_text()
    # 合并多余空白
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _validate_url(url: str) -> None:
    """验证 URL 安全性，防止 SSRF 攻击。

    Args:
        url: 待验证的 URL。

    Raises:
        ValueError: URL 不安全或无效。
    """
    parsed = urlparse(url)

    # 只允许 http/https 协议
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"不支持的协议: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL 缺少主机名")

    # 解析主机名到 IP 地址
    try:
        addrinfos = socket.getaddrinfo(
            hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise ValueError(f"无法解析主机名: {hostname}") from exc

    for family, _, _, _, sockaddr in addrinfos:
        ip_str = sockaddr[0]
        ip = ipaddress.ip_address(ip_str)

        # 检查是否为内网 IP
        for network in _PRIVATE_NETWORKS:
            if ip in network:
                raise ValueError(f"禁止访问内网地址: {ip} ({hostname})")


def create_web_fetch_tool(http_aclient):
    """工厂函数：创建绑定了 http_aclient 的 web_fetch 工具。"""

    @tool
    async def web_fetch(url: str, max_length: int = 8000) -> str:
        """获取网页内容并提取纯文本。

        Args:
            url: 目标 URL。
            max_length: 返回文本最大字符数。
        """
        # SSRF 防护
        _validate_url(url)

        try:
            response = await http_aclient.get(url, follow_redirects=True, timeout=30)
            content_type = response.headers.get("content-type", "")
            body = response.text

            if "html" in content_type:
                text = _html_to_text(body)
            else:
                text = body

            if len(text) > max_length:
                text = text[:max_length] + "\n... [已截断]"
            return text
        except Exception as exc:
            return f"获取失败: {exc}"

    return web_fetch


def create_web_search_tool():
    """工厂函数：创建 web_search 工具。"""

    # 缓存搜索工具引用，避免每次调用都重新发现
    _cached_search_tool: object | None = None
    _cache_valid = False

    @tool
    async def web_search(query: str, num_results: int = 5) -> str:
        """搜索网络获取最新信息。

        优先通过 MCP 搜索服务器执行，若未配置则返回提示。

        Args:
            query: 搜索关键词。
            num_results: 返回结果数量。
        """
        nonlocal _cached_search_tool, _cache_valid

        # 惰性获取 MCP 管理器单例
        from src.ai.core.mcp import mcp_manager

        # 尝试从 MCP 发现可用的搜索工具（带缓存）
        try:
            if not _cache_valid or _cached_search_tool is None:
                tools = await mcp_manager.discover_tools()
                _cached_search_tool = None
                for t in tools:
                    name_lower = t.name.lower()
                    if any(
                        kw in name_lower
                        for kw in ("search", "brave", "tavily", "google", "bing")
                    ):
                        _cached_search_tool = t
                        break
                _cache_valid = True

            if _cached_search_tool is not None:
                result = await _cached_search_tool.ainvoke(
                    {"query": query, "num_results": num_results}
                )
                return (
                    result
                    if isinstance(result, str)
                    else json.dumps(result, ensure_ascii=False, indent=2)
                )
        except Exception as e:
            logger.warning("MCP 搜索工具调用失败: %s", e)
            # 失败时重置缓存，下次重新发现
            _cache_valid = False
            _cached_search_tool = None

        return json.dumps(
            {
                "error": "未配置搜索服务",
                "message": "请在 mcp_servers.json 中配置搜索 MCP 服务器（如 brave-search、tavily 等）",
                "query": query,
            },
            ensure_ascii=False,
            indent=2,
        )

    return web_search


def register(http_aclient):
    """注册网络工具。"""
    web_fetch_tool = create_web_fetch_tool(http_aclient)
    web_search_tool = create_web_search_tool()
    register_tool(
        web_fetch_tool, source_type="builtin", permissions=["external_service"]
    )
    register_tool(
        web_search_tool, source_type="builtin", permissions=["external_service"]
    )
