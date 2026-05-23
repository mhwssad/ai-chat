"""工具服务。"""

from __future__ import annotations

from src.ai.core.tools import ToolCallRequest, tool_manager


class ToolService:
    def list_tools(self, *, enabled_only: bool = False):
        return tool_manager.list_tools(enabled_only=enabled_only)

    async def call_tool(self, request: ToolCallRequest):
        return await tool_manager.execute(request)

