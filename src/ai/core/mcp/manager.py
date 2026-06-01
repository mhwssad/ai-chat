"""MCP 管理器 — 协调配置、客户端和健康检查。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.tools import BaseTool

from src.ai.core.tools.types import ToolPlugin

if TYPE_CHECKING:
    from src.ai.core.tools.registry import ToolRegistry

from .client import MCPClient
from .config import MCPConfigRepository
from .types import MCPHealthResult


class MCPManager(ToolPlugin):
    """MCP 子系统协调器。

    组合 MCPConfigRepository 和 MCPClient，
    提供健康检查等跨组件能力。
    实现 ToolPlugin 接口，支持自动注册 MCP 内置工具。
    """

    def __init__(self, config_repo: MCPConfigRepository) -> None:
        self._config_repo = config_repo
        self._client = MCPClient(config_repo=config_repo)

    @property
    def client(self) -> MCPClient:
        """暴露底层客户端。"""
        return self._client

    async def discover_tools(self, server_key: str | None = None) -> list[BaseTool]:
        """发现 MCP 工具（委托 client）。

        Args:
            server_key: 指定 server 名称，None 表示所有已启用的 server。
        """
        return await self._client.discover_tools(server_key)

    async def call_tool(
        self,
        *,
        server_key: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """调用 MCP 工具（委托 client）。

        Args:
            server_key: MCP server 标识。
            tool_name: 工具名称。
            arguments: 工具参数。
        """
        return await self._client.call_tool(
            server_key=server_key, tool_name=tool_name, arguments=arguments
        )

    async def list_resources(self, server_key: str) -> list[Any]:
        """列出资源（委托 client）。

        Args:
            server_key: MCP server 标识。
        """
        return await self._client.list_resources(server_key)

    async def read_resource(self, *, server_key: str, uri: str) -> list[Any]:
        """读取资源（委托 client）。

        Args:
            server_key: MCP server 标识。
            uri: 资源 URI。
        """
        return await self._client.read_resource(server_key=server_key, uri=uri)

    async def health_check(
        self, server_key: str | None = None
    ) -> list[MCPHealthResult]:
        """检查 MCP server 健康状态。

        Args:
            server_key: 指定 server 名称，None 表示所有已启用的 server。
        """
        configs = self._config_repo.list_enabled()
        if server_key:
            configs = [c for c in configs if c.server_key == server_key]

        results: list[MCPHealthResult] = []
        for config in configs:
            try:
                tools = await self.discover_tools(config.server_key)
                results.append(
                    MCPHealthResult(
                        server_key=config.server_key,
                        status="available",
                        tool_count=len(tools),
                    )
                )
            except Exception as exc:
                results.append(
                    MCPHealthResult(
                        server_key=config.server_key,
                        status="error",
                        message=str(exc),
                    )
                )
        return results

    def register_tools(self, registry: ToolRegistry) -> None:
        """将 MCP 内置工具注册到工具注册表。

        实现 ToolPlugin 接口，由 ToolManager 在加载内置工具时调用。

        Args:
            registry: ToolRegistry 实例。
        """
        from src.ai.core.mcp.tools import create_mcp_tools
        from src.ai.core.tools.registry import ToolMeta

        for tool in create_mcp_tools(self):
            registry.register(
                tool,
                meta=ToolMeta(source_type="mcp", permissions=["external_service"]),
            )
