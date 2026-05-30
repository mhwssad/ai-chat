"""网络工具 — 网页获取和搜索。"""

import json
import re
from html.parser import HTMLParser

from langchain_core.tools import tool

from src.ai.core.tools.register import register_tool


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


def create_web_fetch_tool(http_aclient):
    """工厂函数：创建绑定了 http_aclient 的 web_fetch 工具。"""

    @tool
    async def web_fetch(url: str, max_length: int = 8000) -> str:
        """获取网页内容并提取纯文本。

        Args:
            url: 目标 URL。
            max_length: 返回文本最大字符数。
        """
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


def create_web_search_tool(mcp_manager):
    """工厂函数：创建绑定了 mcp_manager 的 web_search 工具。"""

    @tool
    async def web_search(query: str, num_results: int = 5) -> str:
        """搜索网络获取最新信息。

        优先通过 MCP 搜索服务器执行，若未配置则返回提示。

        Args:
            query: 搜索关键词。
            num_results: 返回结果数量。
        """
        # 尝试从 MCP 发现可用的搜索工具
        try:
            tools = await mcp_manager.discover_tools()
            search_tool = None
            for t in tools:
                name_lower = t.name.lower()
                if any(
                    kw in name_lower
                    for kw in ("search", "brave", "tavily", "google", "bing")
                ):
                    search_tool = t
                    break

            if search_tool is not None:
                result = await search_tool.ainvoke(
                    {"query": query, "num_results": num_results}
                )
                return (
                    result
                    if isinstance(result, str)
                    else json.dumps(result, ensure_ascii=False, indent=2)
                )
        except Exception:
            pass

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


def register(http_aclient, mcp_manager):
    """注册网络工具。"""
    web_fetch_tool = create_web_fetch_tool(http_aclient)
    web_search_tool = create_web_search_tool(mcp_manager)
    register_tool(web_fetch_tool, source_type="builtin", permissions=["external_service"])
    register_tool(web_search_tool, source_type="builtin", permissions=["external_service"])
