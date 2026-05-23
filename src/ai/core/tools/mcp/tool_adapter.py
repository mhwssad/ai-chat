"""MCP 工具到统一模型工具声明的适配。"""

from __future__ import annotations

from src.ai.core.models.types import ToolBinding

from .types import MCPTool


def mcp_tool_to_binding(tool: MCPTool) -> ToolBinding:
    """把 MCP 工具转换为模型层可绑定的 ToolBinding。"""
    return ToolBinding(
        name=tool.binding_name,
        description=tool.description,
        input_schema={
            "type": "function",
            "function": {
                "name": tool.binding_name,
                "description": tool.description,
                "parameters": tool.input_schema or {"type": "object", "properties": {}},
            },
        },
        source_type="mcp",
        source_id=tool.server_key,
        metadata={
            "mcp_tool_name": tool.name,
            "permission_policy": tool.permission_policy,
            **tool.metadata,
        },
    )


def mcp_tools_to_bindings(tools: list[MCPTool]) -> list[ToolBinding]:
    """批量转换 MCP 工具声明。"""
    return [mcp_tool_to_binding(tool) for tool in tools]

