"""定时任务路由。"""

from fastapi import APIRouter

from src.ai.api.deps import SchedulerServiceDep
from src.ai.api.schemas.common import MessageResponse
from src.ai.api.schemas.scheduler import (
    CronTaskCreateRequest,
    IntervalTaskCreateRequest,
    OneShotTaskCreateRequest,
    ScheduledTaskResponse,
    SchedulerStatsResponse,
    TaskLogResponse,
)
from src.ai.core.scheduler.types import TaskType
from src.ai.exception.scheduler_exception import SchedulerNotFoundError

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


def _task_to_response(task) -> ScheduledTaskResponse:
    """转换 ScheduledTaskInfo 为响应格式。"""
    return ScheduledTaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        cron_expr=task.cron_expr,
        interval_seconds=task.interval_seconds,
        one_shot=task.one_shot,
        task_type=task.task_type.value,
        task_config=task.task_config.to_dict(),
        status=task.status.value,
        enabled=task.enabled,
        max_retries=task.max_retries,
        retry_count=task.retry_count,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
        last_run_at=task.last_run_at.isoformat() if task.last_run_at else None,
        next_run_at=task.next_run_at.isoformat() if task.next_run_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        total_runs=task.total_runs,
        success_runs=task.success_runs,
        failed_runs=task.failed_runs,
    )


@router.get("/tasks", response_model=list[ScheduledTaskResponse])
async def list_tasks(
    service: SchedulerServiceDep,
    status: str | None = None,
    enabled: bool | None = None,
    limit: int = 100,
):
    """列出任务。

    Args:
        status: 按状态过滤。
        enabled: 按启用状态过滤。
        limit: 最大返回数量。
    """
    from src.ai.core.scheduler.types import TaskStatus

    status_filter = None
    if status:
        try:
            status_filter = TaskStatus(status)
        except ValueError:
            pass

    tasks = service.list_tasks(status=status_filter, enabled=enabled, limit=limit)
    return [_task_to_response(t) for t in tasks]


@router.get("/stats", response_model=SchedulerStatsResponse)
async def get_scheduler_stats(service: SchedulerServiceDep):
    """获取调度器统计。"""
    stats = service.get_stats()
    return SchedulerStatsResponse(
        scheduler_running=stats.get("scheduler_running", False),
        scheduler_enabled=stats.get("scheduler_enabled", False),
        total_tasks=stats.get("total_tasks", 0),
        active_tasks=stats.get("active_tasks", 0),
        completed_tasks=stats.get("completed_tasks", 0),
        failed_tasks=stats.get("failed_tasks", 0),
    )


@router.post("/tasks/cron", response_model=ScheduledTaskResponse)
async def create_cron_task(
    request: CronTaskCreateRequest,
    service: SchedulerServiceDep,
):
    """创建 Cron 任务。

    Args:
        request: 创建请求。
    """
    task_type = TaskType(request.task_type)
    task = service.create_cron_task(
        name=request.name,
        cron_expr=request.cron_expr,
        task_type=task_type,
        tool_name=request.tool_name,
        tool_args=request.tool_args,
        prompt=request.prompt,
        description=request.description,
        max_retries=request.max_retries,
        metadata=request.metadata,
    )
    return _task_to_response(task)


@router.post("/tasks/interval", response_model=ScheduledTaskResponse)
async def create_interval_task(
    request: IntervalTaskCreateRequest,
    service: SchedulerServiceDep,
):
    """创建间隔任务。

    Args:
        request: 创建请求。
    """
    task_type = TaskType(request.task_type)
    task = service.create_interval_task(
        name=request.name,
        interval_seconds=request.interval_seconds,
        task_type=task_type,
        tool_name=request.tool_name,
        tool_args=request.tool_args,
        prompt=request.prompt,
        description=request.description,
        max_retries=request.max_retries,
        metadata=request.metadata,
    )
    return _task_to_response(task)


@router.post("/tasks/one-shot", response_model=ScheduledTaskResponse)
async def create_one_shot_task(
    request: OneShotTaskCreateRequest,
    service: SchedulerServiceDep,
):
    """创建一次性任务。

    Args:
        request: 创建请求。
    """
    task_type = TaskType(request.task_type)
    task = service.create_one_shot_task(
        name=request.name,
        task_type=task_type,
        tool_name=request.tool_name,
        tool_args=request.tool_args,
        prompt=request.prompt,
        description=request.description,
        metadata=request.metadata,
    )
    return _task_to_response(task)


@router.get("/tasks/{task_id}", response_model=ScheduledTaskResponse)
async def get_task(task_id: str, service: SchedulerServiceDep):
    """获取任务详情。

    Args:
        task_id: 任务 ID。
    """
    task = service.get_task(task_id)
    if task is None:
        raise SchedulerNotFoundError(
            f"任务不存在: {task_id}", context={"task_id": task_id}
        )

    return _task_to_response(task)


@router.delete("/tasks/{task_id}", response_model=MessageResponse)
async def delete_task(task_id: str, service: SchedulerServiceDep):
    """删除任务。

    Args:
        task_id: 任务 ID。
    """
    success = service.delete_task(task_id)
    if not success:
        raise SchedulerNotFoundError(
            f"任务不存在: {task_id}", context={"task_id": task_id}
        )

    return MessageResponse(message=f"任务 {task_id} 已删除")


@router.post("/tasks/{task_id}/enable", response_model=ScheduledTaskResponse)
async def enable_task(task_id: str, service: SchedulerServiceDep):
    """启用任务。

    Args:
        task_id: 任务 ID。
    """
    task = service.enable_task(task_id)
    if task is None:
        raise SchedulerNotFoundError(
            f"任务不存在: {task_id}", context={"task_id": task_id}
        )

    return _task_to_response(task)


@router.post("/tasks/{task_id}/disable", response_model=ScheduledTaskResponse)
async def disable_task(task_id: str, service: SchedulerServiceDep):
    """禁用任务。

    Args:
        task_id: 任务 ID。
    """
    task = service.disable_task(task_id)
    if task is None:
        raise SchedulerNotFoundError(
            f"任务不存在: {task_id}", context={"task_id": task_id}
        )

    return _task_to_response(task)


@router.post("/tasks/{task_id}/pause", response_model=ScheduledTaskResponse)
async def pause_task(task_id: str, service: SchedulerServiceDep):
    """暂停任务。

    Args:
        task_id: 任务 ID。
    """
    task = service.pause_task(task_id)
    if task is None:
        raise SchedulerNotFoundError(
            f"任务不存在: {task_id}", context={"task_id": task_id}
        )

    return _task_to_response(task)


@router.post("/tasks/{task_id}/resume", response_model=ScheduledTaskResponse)
async def resume_task(task_id: str, service: SchedulerServiceDep):
    """恢复任务。

    Args:
        task_id: 任务 ID。
    """
    task = service.resume_task(task_id)
    if task is None:
        raise SchedulerNotFoundError(
            f"任务不存在: {task_id}", context={"task_id": task_id}
        )

    return _task_to_response(task)


@router.get("/tasks/{task_id}/logs", response_model=list[TaskLogResponse])
async def get_task_logs(
    task_id: str,
    service: SchedulerServiceDep,
    limit: int = 50,
):
    """获取任务执行日志。

    Args:
        task_id: 任务 ID。
        limit: 最大返回数量。
    """
    logs = service.get_task_logs(task_id, limit=limit)

    return [
        TaskLogResponse(
            run_id=log["run_id"],
            status=log["status"],
            started_at=log["started_at"],
            finished_at=log["finished_at"],
            duration_ms=log["duration_ms"],
            result_summary=log["result_summary"],
            error_type=log["error_type"],
            error_message=log["error_message"],
        )
        for log in logs
    ]
