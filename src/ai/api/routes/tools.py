"""工具路由。"""

from fastapi import APIRouter

from src.ai.api.deps import ToolServiceDep
from src.ai.api.schemas.tools import (
    ToolExecuteRequest,
    ToolExecuteResponse,
    ToolMetaResponse,
    ToolPermissionRequest,
    ToolPermissionResponse,
    ToolSchemaResponse,
)

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=list[ToolMetaResponse])
async def list_tools(
    service: ToolServiceDep,
    enabled_only: bool = True,
):
    """列出已注册工具。

    Args:
        enabled_only: 是否只返回启用的工具。
    """
    tools = service.list_tools(enabled_only=enabled_only)
    return [
        ToolMetaResponse(
            name=t["name"],
            display_name=t["display_name"],
            description=t["description"],
            source_type=t["source_type"],
            source_id=t["source_id"],
            permissions=t["permissions"],
            output_description=t["output_description"],
            essential=t["essential"],
            enabled=t["enabled"],
        )
        for t in tools
    ]


@router.get("/schemas", response_model=list[ToolSchemaResponse])
async def list_tool_schemas(
    service: ToolServiceDep,
    enabled_only: bool = True,
):
    """列出工具的 OpenAI function-calling schema。

    Args:
        enabled_only: 是否只返回启用的工具。
    """
    schemas = service.list_schemas(enabled_only=enabled_only)
    return [ToolSchemaResponse(type=s["type"], function=s["function"]) for s in schemas]


@router.post("/{name}/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    name: str,
    request: ToolExecuteRequest,
    service: ToolServiceDep,
):
    """执行工具。

    Args:
        name: 工具名称。
        request: 执行请求。
    """
    diagnostic = await service.execute_tool_diagnostic(name, request.arguments)
    return ToolExecuteResponse(
        result=diagnostic.result,
        tool_name=diagnostic.tool_name,
        status=diagnostic.status,
        duration_ms=diagnostic.duration_ms,
        permission_decision=diagnostic.permission_decision,
        input_summary=diagnostic.input_summary,
        output_summary=diagnostic.output_summary,
        error_type=diagnostic.error_type,
        error_message=diagnostic.error_message,
    )


@router.post("/{name}/permission", response_model=ToolPermissionResponse)
async def check_tool_permission(
    name: str,
    request: ToolPermissionRequest,
    service: ToolServiceDep,
):
    """检查工具权限决策。"""
    decision = await service.check_permission(name, request.arguments)
    if decision is None:
        decision = {
            "decision": "allow",
            "tool_name": name,
            "permissions": [],
            "reason": "permission_checker_disabled",
            "confirmed": None,
            "cached": False,
            "context": {},
        }
    return ToolPermissionResponse(**decision)
