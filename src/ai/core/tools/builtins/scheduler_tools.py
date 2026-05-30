"""定时任务工具。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.ai.core.tools.register import register_tool

if TYPE_CHECKING:
    from src.ai.core.scheduler.service import SchedulerService


# ── 参数 Schema ───────────────────────────────────────────────────────────────


class CronCreateArgs(BaseModel):
    """创建定时任务参数。"""

    name: str = Field(description="任务名称（必须唯一）")
    cron: str = Field(
        description="Cron 表达式（5 位：分 时 日 月 周），例如 '0 9 * * *' 表示每天 9 点"
    )
    prompt: str = Field(description="任务执行的提示词或工具调用指令")
    description: str | None = Field(default=None, description="任务描述")


class CronDeleteArgs(BaseModel):
    """删除定时任务参数。"""

    task_id: str = Field(description="任务 ID")


class CronListArgs(BaseModel):
    """列出定时任务参数。"""

    status: str | None = Field(
        default=None,
        description="按状态过滤：active / paused / completed / failed / disabled",
    )
    limit: int = Field(default=50, description="返回数量限制")


# ── 工具实现 ──────────────────────────────────────────────────────────────────


def _create_scheduler_tools(
    scheduler_service: SchedulerService,
) -> list[StructuredTool]:
    """创建定时任务工具。"""

    async def cron_create(
        name: str,
        cron: str,
        prompt: str,
        description: str | None = None,
    ) -> str:
        """创建定时任务。

        创建一个基于 Cron 表达式调度的定时任务。
        任务将在指定时间自动执行给定的提示词。

        Args:
            name: 任务名称（必须唯一）。
            cron: Cron 表达式（5 位：分 时 日 月 周）。
            prompt: 任务执行的提示词。
            description: 任务描述。

        Returns:
            创建结果的 JSON 字符串。
        """
        try:
            from src.ai.core.scheduler.types import TaskType

            task = scheduler_service.create_cron_task(
                name=name,
                cron_expr=cron,
                task_type=TaskType.LLM_PROMPT,
                prompt=prompt,
                description=description,
            )

            return json.dumps(
                {
                    "success": True,
                    "task_id": task.id,
                    "name": task.name,
                    "cron": task.cron_expr,
                    "next_run_at": task.next_run_at.isoformat()
                    if task.next_run_at
                    else None,
                    "message": f"定时任务 '{name}' 创建成功",
                },
                ensure_ascii=False,
            )
        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                    "message": f"创建定时任务失败: {str(e)}",
                },
                ensure_ascii=False,
            )

    async def cron_delete(task_id: str) -> str:
        """删除定时任务。

        删除指定的定时任务。

        Args:
            task_id: 任务 ID。

        Returns:
            删除结果的 JSON 字符串。
        """
        try:
            # 先获取任务信息
            task = scheduler_service.get_task(task_id)
            if not task:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Task not found",
                        "message": f"任务 {task_id} 不存在",
                    },
                    ensure_ascii=False,
                )

            # 删除任务
            success = scheduler_service.delete_task(task_id)

            if success:
                return json.dumps(
                    {
                        "success": True,
                        "task_id": task_id,
                        "name": task.name,
                        "message": f"定时任务 '{task.name}' 已删除",
                    },
                    ensure_ascii=False,
                )
            else:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Delete failed",
                        "message": f"删除任务 {task_id} 失败",
                    },
                    ensure_ascii=False,
                )
        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                    "message": f"删除定时任务失败: {str(e)}",
                },
                ensure_ascii=False,
            )

    async def cron_list(
        status: str | None = None,
        limit: int = 50,
    ) -> str:
        """列出定时任务。

        列出所有定时任务，可按状态过滤。

        Args:
            status: 按状态过滤（active / paused / completed / failed / disabled）。
            limit: 返回数量限制。

        Returns:
            任务列表的 JSON 字符串。
        """
        try:
            from src.ai.core.scheduler.types import TaskStatus

            # 解析状态过滤
            status_filter = None
            if status:
                try:
                    status_filter = TaskStatus(status)
                except ValueError:
                    return json.dumps(
                        {
                            "success": False,
                            "error": f"Invalid status: {status}",
                            "message": f"无效的状态: {status}，有效值: active, paused, completed, failed, disabled",
                        },
                        ensure_ascii=False,
                    )

            # 获取任务列表
            tasks = scheduler_service.list_tasks(
                status=status_filter,
                limit=limit,
            )

            # 转换为字典列表
            task_list = []
            for task in tasks:
                task_list.append(
                    {
                        "task_id": task.id,
                        "name": task.name,
                        "description": task.description,
                        "cron": task.cron_expr,
                        "interval_seconds": task.interval_seconds,
                        "one_shot": task.one_shot,
                        "task_type": task.task_type.value,
                        "status": task.status.value,
                        "enabled": task.enabled,
                        "total_runs": task.total_runs,
                        "success_runs": task.success_runs,
                        "failed_runs": task.failed_runs,
                        "last_run_at": task.last_run_at.isoformat()
                        if task.last_run_at
                        else None,
                        "next_run_at": task.next_run_at.isoformat()
                        if task.next_run_at
                        else None,
                        "created_at": task.created_at.isoformat(),
                    }
                )

            return json.dumps(
                {
                    "success": True,
                    "total": len(task_list),
                    "tasks": task_list,
                },
                ensure_ascii=False,
            )
        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                    "message": f"获取任务列表失败: {str(e)}",
                },
                ensure_ascii=False,
            )

    # 创建工具实例
    cron_create_tool = StructuredTool.from_function(
        coroutine=cron_create,
        name="CronCreate",
        description="创建定时任务。使用 Cron 表达式调度任务在指定时间执行。",
        args_schema=CronCreateArgs,
    )

    cron_delete_tool = StructuredTool.from_function(
        coroutine=cron_delete,
        name="CronDelete",
        description="删除定时任务。删除指定的定时任务。",
        args_schema=CronDeleteArgs,
    )

    cron_list_tool = StructuredTool.from_function(
        coroutine=cron_list,
        name="CronList",
        description="列出定时任务。列出所有定时任务，可按状态过滤。",
        args_schema=CronListArgs,
    )

    return [cron_create_tool, cron_delete_tool, cron_list_tool]


# ── 注册接口 ──────────────────────────────────────────────────────────────────


def register(scheduler_service: SchedulerService) -> None:
    """注册定时任务工具。

    由 builtins/__init__.py 的 register_dependent_tools() 调用。

    Args:
        scheduler_service: 定时任务服务实例。
    """
    tools = _create_scheduler_tools(scheduler_service)
    for tool in tools:
        register_tool(tool, source_type="builtin")
