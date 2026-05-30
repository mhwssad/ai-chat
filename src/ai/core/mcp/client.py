"""MCP 客户端 — 封装 MultiServerMCPClient 的生命周期和底层操作。"""

import hashlib
import json
import logging
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from .adapter import to_langchain_connections
from .config import MCPConfigRepository

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP 底层客户端。

    职责：
    - MultiServerMCPClient 懒创建 + 配置哈希变更检测
    - 工具发现（返回 langchain BaseTool）
    - 工具调用（通过 session 直接调用）
    - 资源访问（list / read）
    """

    def __init__(self, config_repo: MCPConfigRepository) -> None:
        self._config_repo = config_repo
        self._client: MultiServerMCPClient | None = None
        self._config_hash: str | None = None

    def _get_client(self) -> MultiServerMCPClient:
        """懒创建 MultiServerMCPClient，配置变化时重建。"""
        configs = self._config_repo.list_enabled()
        connections = to_langchain_connections(configs)
        config_hash = hashlib.md5(
            json.dumps(connections, sort_keys=True, default=str).encode()
        ).hexdigest()
        if self._client is None or config_hash != self._config_hash:
            self._client = MultiServerMCPClient(connections, tool_name_prefix=True)
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

        Args:
            server_key: MCP server 标识。
            tool_name: 工具名称。
            arguments: 工具参数。
        """
        client = self._get_client()
        async with client.session(server_key) as session:
            return await session.call_tool(tool_name, arguments or {})

    async def list_resources(self, server_key: str) -> list[Any]:
        """列出 MCP server 资源。

        Args:
            server_key: MCP server 标识。
        """
        client = self._get_client()
        return await client.get_resources(server_name=server_key)

    async def read_resource(self, *, server_key: str, uri: str) -> list[Any]:
        """读取 MCP server 资源。

        Args:
            server_key: MCP server 标识。
            uri: 资源 URI。
        """
        client = self._get_client()
        return await client.get_resources(server_name=server_key, uris=uri)
