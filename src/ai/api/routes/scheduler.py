"""定时任务路由 — 任务 CRUD、状态管理、执行日志。"""

from __future__ import annotations

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query

from src.ai.api.schemas.common import MessageResponse
from src.ai.api.schemas.scheduler import (
    SchedulerCreateCronRequest,
    SchedulerCreateIntervalRequest,
    SchedulerCreateOneShotRequest,
    SchedulerStatsResponse,
    ScheduledTaskResponse,
    TaskLogResponse,
)
from src.ai.core.container import AppContainer
from src.ai.service.scheduler_service import SchedulerApiService

router = APIRouter()


@router.post(
    "/tasks/cron", response_model=ScheduledTaskResponse, summary="创建 cron 任务"
)
@inject
async def create_cron_task(
    req: SchedulerCreateCronRequest,
    svc: Annotated[
        SchedulerApiService,
        Depends(Provide[AppContainer.service_container.scheduler_api_service]),
    ],
) -> ScheduledTaskResponse:
    """创建 cron 定时任务。"""
    data = svc.create_cron_task(
        name=req.name,
        cron_expr=req.cron_expr,
        task_type=req.task_type,
        tool_name=req.tool_name,
        tool_args=req.tool_args,
        prompt=req.prompt,
        description=req.description,
        max_retries=req.max_retries,
        metadata=req.metadata,
    )
    return ScheduledTaskResponse(**data)


@router.post(
    "/tasks/interval", response_model=ScheduledTaskResponse, summary="创建间隔任务"
)
@inject
async def create_interval_task(
    req: SchedulerCreateIntervalRequest,
    svc: Annotated[
        SchedulerApiService,
        Depends(Provide[AppContainer.service_container.scheduler_api_service]),
    ],
) -> ScheduledTaskResponse:
    """创建间隔定时任务。"""
    data = svc.create_interval_task(
        name=req.name,
        interval_seconds=req.interval_seconds,
        task_type=req.task_type,
        tool_name=req.tool_name,
        tool_args=req.tool_args,
        prompt=req.prompt,
        description=req.description,
        max_retries=req.max_retries,
        metadata=req.metadata,
    )
    return ScheduledTaskResponse(**data)


@router.post(
    "/tasks/one-shot", response_model=ScheduledTaskResponse, summary="创建一次性任务"
)
@inject
async def create_one_shot_task(
    req: SchedulerCreateOneShotRequest,
    svc: Annotated[
        SchedulerApiService,
        Depends(Provide[AppContainer.service_container.scheduler_api_service]),
    ],
) -> ScheduledTaskResponse:
    """创建一次性任务。"""
    data = svc.create_one_shot_task(
        name=req.name,
        task_type=req.task_type,
        tool_name=req.tool_name,
        tool_args=req.tool_args,
        prompt=req.prompt,
        description=req.description,
        metadata=req.metadata,
    )
    return ScheduledTaskResponse(**data)


@router.get("/tasks", response_model=list[ScheduledTaskResponse], summary="列出任务")
@inject
async def list_tasks(
    svc: Annotated[
        SchedulerApiService,
        Depends(Provide[AppContainer.service_container.scheduler_api_service]),
    ],
    status: str | None = Query(default=None, description="按状态过滤"),
    enabled: bool | None = Query(default=None, description="按启用状态过滤"),
    limit: int = Query(default=100, ge=1, le=500, description="最大返回数量"),
) -> list[ScheduledTaskResponse]:
    """列出定时任务。"""
    tasks = svc.list_tasks(status=status, enabled=enabled, limit=limit)
    return [ScheduledTaskResponse(**t) for t in tasks]


@router.get(
    "/tasks/{task_id}", response_model=ScheduledTaskResponse, summary="获取任务"
)
@inject
async def get_task(
    task_id: str,
    svc: Annotated[
        SchedulerApiService,
        Depends(Provide[AppContainer.service_container.scheduler_api_service]),
    ],
) -> ScheduledTaskResponse:
    """获取指定定时任务。"""
    task = svc.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return ScheduledTaskResponse(**task)


@router.delete("/tasks/{task_id}", response_model=MessageResponse, summary="删除任务")
@inject
async def delete_task(
    task_id: str,
    svc: Annotated[
        SchedulerApiService,
        Depends(Provide[AppContainer.service_container.scheduler_api_service]),
    ],
) -> MessageResponse:
    """删除定时任务。"""
    deleted = svc.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return MessageResponse(message=f"已删除: {task_id}")


@router.post(
    "/tasks/{task_id}/enable", response_model=ScheduledTaskResponse, summary="启用任务"
)
@inject
async def enable_task(
    task_id: str,
    svc: Annotated[
        SchedulerApiService,
        Depends(Provide[AppContainer.service_container.scheduler_api_service]),
    ],
) -> ScheduledTaskResponse:
    """启用定时任务。"""
    task = svc.enable_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return ScheduledTaskResponse(**task)


@router.post(
    "/tasks/{task_id}/disable", response_model=ScheduledTaskResponse, summary="禁用任务"
)
@inject
async def disable_task(
    task_id: str,
    svc: Annotated[
        SchedulerApiService,
        Depends(Provide[AppContainer.service_container.scheduler_api_service]),
    ],
) -> ScheduledTaskResponse:
    """禁用定时任务。"""
    task = svc.disable_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return ScheduledTaskResponse(**task)


@router.post(
    "/tasks/{task_id}/pause", response_model=ScheduledTaskResponse, summary="暂停任务"
)
@inject
async def pause_task(
    task_id: str,
    svc: Annotated[
        SchedulerApiService,
        Depends(Provide[AppContainer.service_container.scheduler_api_service]),
    ],
) -> ScheduledTaskResponse:
    """暂停定时任务。"""
    task = svc.pause_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return ScheduledTaskResponse(**task)


@router.post(
    "/tasks/{task_id}/resume", response_model=ScheduledTaskResponse, summary="恢复任务"
)
@inject
async def resume_task(
    task_id: str,
    svc: Annotated[
        SchedulerApiService,
        Depends(Provide[AppContainer.service_container.scheduler_api_service]),
    ],
) -> ScheduledTaskResponse:
    """恢复定时任务。"""
    task = svc.resume_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return ScheduledTaskResponse(**task)


@router.get(
    "/tasks/{task_id}/logs", response_model=list[TaskLogResponse], summary="执行日志"
)
@inject
async def get_task_logs(
    task_id: str,
    svc: Annotated[
        SchedulerApiService,
        Depends(Provide[AppContainer.service_container.scheduler_api_service]),
    ],
    limit: int = Query(default=50, ge=1, le=200, description="最大返回数量"),
) -> list[TaskLogResponse]:
    """获取任务执行日志。"""
    logs = svc.get_task_logs(task_id, limit=limit)
    return [TaskLogResponse(**log) for log in logs]


@router.get("/stats", response_model=SchedulerStatsResponse, summary="调度器统计")
@inject
async def get_stats(
    svc: Annotated[
        SchedulerApiService,
        Depends(Provide[AppContainer.service_container.scheduler_api_service]),
    ],
) -> SchedulerStatsResponse:
    """获取调度器统计信息。"""
    stats = svc.get_stats()
    return SchedulerStatsResponse(**stats)
