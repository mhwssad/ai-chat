"""工具路由。"""

from fastapi import APIRouter

from src.ai.api.deps import ToolManagerDep, ToolRegistryDep
from src.ai.api.schemas.tools import (
    ToolExecuteRequest,
    ToolExecuteResponse,
    ToolMetaResponse,
    ToolSchemaResponse,
)

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=list[ToolMetaResponse])
async def list_tools(
    registry: ToolRegistryDep,
    enabled_only: bool = True,
):
    """列出已注册工具。

    Args:
        enabled_only: 是否只返回启用的工具。
    """
    tools = registry.list(enabled_only=enabled_only)
    result = []
    for tool in tools:
        meta = registry.get_meta(tool.name)
        result.append(
            ToolMetaResponse(
                name=tool.name,
                description=tool.description or "",
                source_type=meta.source_type,
                source_id=meta.source_id,
                permissions=meta.permissions,
                essential=meta.essential,
                enabled=meta.enabled,
            )
        )
    return result


@router.get("/schemas", response_model=list[ToolSchemaResponse])
async def list_tool_schemas(
    manager: ToolManagerDep,
    enabled_only: bool = True,
):
    """列出工具的 OpenAI function-calling schema。

    Args:
        enabled_only: 是否只返回启用的工具。
    """
    schemas = manager.list_schemas(enabled_only=enabled_only)
    return [ToolSchemaResponse(type=s["type"], function=s["function"]) for s in schemas]


@router.post("/{name}/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    name: str,
    request: ToolExecuteRequest,
    manager: ToolManagerDep,
):
    """执行工具。

    Args:
        name: 工具名称。
        request: 执行请求。
    """
    result = await manager.execute(name, request.arguments)
    return ToolExecuteResponse(result=result, tool_name=name)
