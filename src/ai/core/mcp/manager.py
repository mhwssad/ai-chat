"""MCP server 管理器 — 使用 langchain-mcp-adapters。"""

import logging
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from .config import MCPConfigRepository
from .types import MCPHealthResult

logger = logging.getLogger(__name__)


class MCPManager:
    """管理 MCP server 配置、工具发现和资源访问。

    内部使用 langchain-mcp-adapters 的 MultiServerMCPClient 管理连接，
    discover_tools() 返回 langchain 原生 BaseTool 列表。
    """

    def __init__(self) -> None:
        self._config_repo = MCPConfigRepository()
        self._client: MultiServerMCPClient | None = None
        self._config_hash: str | None = None

    def _get_client(self) -> MultiServerMCPClient:
        """懒创建 MultiServerMCPClient，配置变化时重建。"""
        connections = self._config_repo.to_connections()
        config_hash = str(sorted(connections.keys()))
        if self._client is None or config_hash != self._config_hash:
            self._client = MultiServerMCPClient(
                connections,
                tool_name_prefix=True,
            )
            self._config_hash = config_hash
        return self._client

    async def discover_tools(self, server_key: str | None = None) -> list[BaseTool]:
        """发现 MCP 工具，返回 langchain BaseTool 列表。

        Args:
            server_key: 指定 server 名称，None 表示所有已启用的 server。
        """
        client = self._get_client()
        return await client.get_tools(server_name=server_key)

    async def call_tool(
        self,
        *,
        server_key: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """调用 MCP 工具。

        通过 session 直接调用，返回 MCP SDK 原生结果。
        """
        client = self._get_client()
        async with client.session(server_key) as session:
            return await session.call_tool(tool_name, arguments or {})

    async def list_resources(self, server_key: str) -> list[Any]:
        """列出 MCP server 资源。"""
        client = self._get_client()
        return await client.get_resources(server_name=server_key)

    async def read_resource(self, *, server_key: str, uri: str) -> list[Any]:
        """读取 MCP server 资源。"""
        client = self._get_client()
        return await client.get_resources(server_name=server_key, uris=uri)

    async def health_check(self, server_key: str | None = None) -> list[MCPHealthResult]:
        """检查 MCP server 健康状态。"""
        configs = self._config_repo.list_enabled()
        if server_key:
            configs = [c for c in configs if c.server_key == server_key]

        results: list[MCPHealthResult] = []
        for config in configs:
            try:
                tools = await self.discover_tools(config.server_key)
                results.append(MCPHealthResult(
                    server_key=config.server_key,
                    status="available",
                    tool_count=len(tools),
                ))
            except Exception as exc:
                results.append(MCPHealthResult(
                    server_key=config.server_key,
                    status="error",
                    message=str(exc),
                ))
        return results


mcp_manager = MCPManager()
