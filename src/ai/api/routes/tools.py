"""工具管理路由。"""

from __future__ import annotations

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query

from src.ai.api.schemas.tools import (
    ToolDetail,
    ToolExecuteRequest,
    ToolExecuteResponse,
    ToolInfo,
)
from src.ai.core.container import AppContainer
from src.ai.service.tool_service import ToolService

router = APIRouter()


@router.get("", response_model=list[ToolInfo], summary="获取工具列表")
@inject
async def list_tools(
    svc: Annotated[
        ToolService, Depends(Provide[AppContainer.service_container.tool_service])
    ],
    enabled_only: bool = Query(default=True, description="仅返回启用的工具"),
) -> list[ToolInfo]:
    """返回工具列表。"""
    tools = svc.list_tools(enabled_only=enabled_only)
    return [ToolInfo(**t) for t in tools]


@router.get("/{name}", response_model=ToolDetail, summary="获取工具详情")
@inject
async def get_tool_detail(
    name: str,
    svc: Annotated[
        ToolService, Depends(Provide[AppContainer.service_container.tool_service])
    ],
) -> ToolDetail:
    """返回工具详情（含参数 schema）。"""
    try:
        detail = svc.get_tool_detail(name)
        return ToolDetail(**detail)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"工具不存在: {name}")


@router.post(
    "/{name}/execute", response_model=ToolExecuteResponse, summary="测试执行工具"
)
@inject
async def execute_tool(
    name: str,
    req: ToolExecuteRequest,
    svc: Annotated[
        ToolService, Depends(Provide[AppContainer.service_container.tool_service])
    ],
) -> ToolExecuteResponse:
    """测试执行工具并返回诊断结果。"""
    try:
        diagnostic = await svc.execute_tool_diagnostic(
            name,
            req.arguments,
            timeout=req.timeout,
        )
        return ToolExecuteResponse(
            tool_name=diagnostic.tool_name,
            source_type=diagnostic.source_type,
            source_id=diagnostic.source_id,
            status=diagnostic.status,
            duration_ms=diagnostic.duration_ms,
            permission_decision=diagnostic.permission_decision,
            input_summary=diagnostic.input_summary,
            output_summary=diagnostic.output_summary,
            error_type=diagnostic.error_type,
            error_message=diagnostic.error_message,
            result=diagnostic.result,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"工具不存在: {name}")
