"""统一工具管理器。"""

from __future__ import annotations

import anyio
from functools import partial

from .adapters import tools_to_bindings
from .builtins import get_builtin_tools
from .executor import ToolExecutor
from .mcp import MCPTool, mcp_manager
from .registry import ToolRegistry, tool_registry
from .types import ToolCallRequest, ToolCallResult, ToolDefinition


class ToolManager:
    """组装、发现和执行统一工具池。"""

    def __init__(self, registry: ToolRegistry = tool_registry) -> None:
        self.registry = registry
        self.executor = ToolExecutor(registry)

    def load_builtin_tools(self) -> None:
        self.registry.register_many(get_builtin_tools())

    async def load_mcp_tools(self, server_key: str | None = None) -> None:
        tools = await mcp_manager.discover_tools(server_key)
        self.registry.register_many([self._mcp_tool_to_definition(tool) for tool in tools])

    def load_skill_tools(self, *, discover: bool = False) -> None:
        from src.ai.core.skils.service import skill_service

        if discover:
            skill_service.discover_and_sync()
        self.registry.register_many(skill_service.tool_definitions())

    async def refresh(self, *, include_mcp: bool = True, include_skills: bool = True) -> None:
        self.registry.clear()
        self.load_builtin_tools()
        if include_skills:
            self.load_skill_tools()
        if include_mcp:
            await self.load_mcp_tools()

    def refresh_sync(self, *, include_mcp: bool = True, include_skills: bool = True) -> None:
        anyio.run(partial(self.refresh, include_mcp=include_mcp, include_skills=include_skills))

    def list_tools(self, *, enabled_only: bool = False) -> list[ToolDefinition]:
        return self.registry.list(enabled_only=enabled_only)

    def list_tool_bindings(self, *, enabled_only: bool = True):
        return tools_to_bindings(self.list_tools(enabled_only=enabled_only))

    async def execute(self, request: ToolCallRequest) -> ToolCallResult:
        return await self.executor.execute(request)

    def execute_sync(self, request: ToolCallRequest) -> ToolCallResult:
        return self.executor.execute_sync(request)

    def _mcp_tool_to_definition(self, tool: MCPTool) -> ToolDefinition:
        async def handler(request: ToolCallRequest) -> ToolCallResult:
            result = await mcp_manager.call_tool(
                server_key=tool.server_key,
                tool_name=tool.name,
                arguments=request.arguments,
                session_id=request.session_id,
                record_audit=False,
            )
            return ToolCallResult(
                tool_name=request.tool_name,
                content=result.content,
                structured_content=result.structured_content,
                is_error=result.is_error,
                raw=result.raw,
            )

        return ToolDefinition(
            name=tool.binding_name,
            display_name=tool.name,
            description=tool.description,
            source_type="mcp",
            source_id=tool.server_key,
            input_schema=tool.input_schema,
            output_schema=tool.output_schema,
            permissions=list(tool.permission_policy.get("permissions", [])),
            handler=handler,
            metadata={
                "mcp_tool_name": tool.name,
                "permission_policy": tool.permission_policy,
                **tool.metadata,
            },
        )


tool_manager = ToolManager()
tool_manager.load_builtin_tools()
