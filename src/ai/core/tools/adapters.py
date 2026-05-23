"""工具层适配器。"""

from __future__ import annotations

from src.ai.core.models.types import ToolBinding

from .types import ToolDefinition


def tool_to_binding(tool: ToolDefinition) -> ToolBinding:
    """把统一工具定义转换为模型层 ToolBinding。"""
    return ToolBinding(
        name=tool.name,
        description=tool.description,
        input_schema={
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema or {"type": "object", "properties": {}},
            },
        },
        source_type=tool.source_type,
        source_id=tool.source_id,
        metadata={
            "permissions": tool.permissions,
            "timeout_seconds": tool.timeout_seconds,
            **tool.metadata,
        },
    )


def tools_to_bindings(tools: list[ToolDefinition]) -> list[ToolBinding]:
    """批量转换工具定义。"""
    return [tool_to_binding(tool) for tool in tools if tool.enabled]

