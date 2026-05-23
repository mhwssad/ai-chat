"""模型工具绑定协议。"""

from __future__ import annotations

from src.ai.exception.llm_exception import LLMException

from .types import ToolBinding


def normalize_tools(tools: list[ToolBinding]) -> list[ToolBinding]:
    """统一工具绑定入口，覆盖 builtin、MCP 和 skills。"""
    normalized: list[ToolBinding] = []
    for tool in tools:
        if not tool.name:
            raise LLMException("工具名称不能为空")
        schema = normalize_tool_schema(tool)
        normalized.append(
            ToolBinding(
                name=tool.name,
                description=tool.description,
                input_schema=schema,
                source_type=tool.source_type,
                source_id=tool.source_id,
                metadata=tool.metadata,
            )
        )
    return normalized


def normalize_tool_schema(tool: ToolBinding) -> dict:
    """转换为 OpenAI/LangChain 常见 function tool schema。"""
    schema = dict(tool.input_schema or {})
    if schema.get("type") == "function" and "function" in schema:
        return schema

    if "name" in schema and "parameters" in schema:
        return {
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema.get("description", tool.description),
                "parameters": schema["parameters"],
            },
        }

    parameters = schema
    if not parameters:
        parameters = {"type": "object", "properties": {}, "additionalProperties": False}
    elif parameters.get("type") != "object":
        parameters = {"type": "object", "properties": schema}

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": parameters,
        },
    }
