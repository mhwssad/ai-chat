"""MCP 服务。"""

from __future__ import annotations

from src.ai.core.tools.mcp import mcp_manager


class MCPService:
    def list_servers(self):
        return mcp_manager.list_enabled_servers()

    async def list_tools(self, server_key: str | None = None):
        return await mcp_manager.discover_tools(server_key)

    async def health_check(self, server_key: str | None = None):
        return await mcp_manager.health_check(server_key)

