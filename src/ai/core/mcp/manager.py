"""MCP 管理器 — 协调配置、客户端、工具同步和健康检查。"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from langchain_core.tools import BaseTool

from src.ai.core.callbacks.audit import AuditEvent, record_audit_event
from src.ai.core.tools.types import ToolPlugin

if TYPE_CHECKING:
    from src.ai.core.tools.registry import ToolRegistry

from .client import MCPClient
from .config import MCPConfigRepository
from .types import MCPHealthResult

logger = logging.getLogger(__name__)


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
        all_configs = self._config_repo.list_all()
        if not all_configs:
            return [
                MCPHealthResult(
                    server_key=server_key or "*",
                    status="not_configured",
                    message="未配置 MCP server",
                )
            ]

        selected_configs = all_configs
        if server_key:
            selected_configs = [c for c in all_configs if c.server_key == server_key]
            if not selected_configs:
                return [
                    MCPHealthResult(
                        server_key=server_key,
                        status="not_configured",
                        message="指定 MCP server 不存在",
                    )
                ]

        results: list[MCPHealthResult] = []
        for config in selected_configs:
            if not config.enabled:
                results.append(
                    MCPHealthResult(
                        server_key=config.server_key,
                        status="configured",
                        message="MCP server 已配置但未启用",
                    )
                )
                continue
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

    async def sync_tools(self, registry: ToolRegistry) -> None:
        """发现启用的 MCP server 工具并同步到统一工具注册表。"""
        from src.ai.core.tools.types import ToolMeta

        configs = self._config_repo.list_enabled()
        for config in configs:
            try:
                tools = await self.discover_tools(config.server_key)
            except Exception:
                record_audit_event(
                    AuditEvent(
                        event_type="mcp_tool_sync",
                        source_module="mcp",
                        target=config.server_key,
                        status="failed",
                        error_type="MCPToolDiscoveryError",
                        error_message="MCP 工具发现失败",
                    )
                )
                logger.debug(
                    "MCP 工具同步失败: server_key=%s",
                    config.server_key,
                    exc_info=True,
                )
                continue

            permissions = self._permissions_from_policy(config.permission_policy)
            for tool in tools:
                registry.register(
                    tool,
                    meta=ToolMeta(
                        source_type="mcp",
                        source_id=config.server_key,
                        display_name=getattr(tool, "name", None),
                        permissions=permissions,
                        output_description="MCP server 返回结果",
                    ),
                )
            record_audit_event(
                AuditEvent(
                    event_type="mcp_tool_sync",
                    source_module="mcp",
                    target=config.server_key,
                    output_summary=f"同步工具数={len(tools)}",
                    status="success",
                )
            )

    def register_tools(self, registry: ToolRegistry) -> None:
        """将 MCP 资源工具和已发现的 server 工具注册到工具注册表。

        实现 ToolPlugin 接口，由 ToolManager 在加载内置工具时调用。

        Args:
            registry: ToolRegistry 实例。
        """
        from src.ai.core.mcp.tools import create_mcp_tools
        from src.ai.core.tools.types import ToolMeta

        for tool in create_mcp_tools(self):
            registry.register(
                tool,
                meta=ToolMeta(
                    source_type="mcp",
                    source_id="mcp_runtime",
                    display_name=tool.name,
                    permissions=["external_service"],
                ),
            )

        self._schedule_or_run_sync(registry)

    def _schedule_or_run_sync(self, registry: ToolRegistry) -> None:
        """在当前上下文中安全触发 MCP 工具同步。"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                asyncio.run(self.sync_tools(registry))
            except Exception:
                logger.debug("同步 MCP 工具失败", exc_info=True)
            return

        loop.create_task(self.sync_tools(registry))

    @staticmethod
    def _permissions_from_policy(policy: dict[str, Any]) -> list[str]:
        """从 MCP 权限策略提取工具权限标签。"""
        permissions = policy.get("permissions")
        if isinstance(permissions, list):
            values = [str(item) for item in permissions if str(item).strip()]
            if values:
                return values
        return ["external_service"]
