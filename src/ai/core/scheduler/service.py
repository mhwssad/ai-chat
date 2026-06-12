"""定时任务服务门面。

职责：完整的业务服务层，负责：
1. 参数验证
2. 业务规则检查
3. 状态管理
4. 执行统计更新
5. 日志查询
"""

from __future__ import annotations

from src.ai.config.logging_setup import get_logger
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from croniter import croniter

from src.ai.core.scheduler.manager import SchedulerManager
from src.ai.core.scheduler.store import SchedulerStore
from src.ai.core.scheduler.types import (
    ScheduledTaskInfo,
    TaskConfig,
    TaskStatus,
    TaskType,
)

if TYPE_CHECKING:
    from src.ai.config.settings import SchedulerSettings

logger = get_logger(__name__)


class SchedulerService:
    """定时任务服务门面。

    职责：完整的业务服务层，负责：
    1. 参数验证和业务规则检查
    2. 任务 CRUD 操作
    3. 状态管理（enable/disable/pause/resume）
    4. 执行统计更新（重试逻辑、状态转换）
    5. 日志查询

    不负责：
    - 调度循环（由 SchedulerManager 处理）
    - 任务执行（由 TaskExecutor 处理）
    - 数据持久化（由 SchedulerStore 处理）
    """

    def __init__(
        self,
        *,
        manager: SchedulerManager,
        store: SchedulerStore,
        settings: SchedulerSettings,
    ) -> None:
        self._manager = manager
        self._store = store
        self._settings = settings

    @property
    def is_running(self) -> bool:
        """调度器是否正在运行。"""
        return self._manager.is_running

    async def start(self) -> None:
        """启动调度器。"""
        await self._manager.start()

    async def stop(self) -> None:
        """停止调度器。"""
        await self._manager.stop()

    # ── 任务管理 ──────────────────────────────────────────────

    def create_cron_task(
        self,
        *,
        name: str,
        cron_expr: str,
        task_type: TaskType = TaskType.TOOL_CALL,
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
        prompt: str | None = None,
        description: str | None = None,
        max_retries: int | None = None,
        metadata: dict | None = None,
    ) -> ScheduledTaskInfo:
        """创建基于 Cron 表达式的定时任务。

        Args:
            name: 任务名称（必须唯一）。
            cron_expr: Cron 表达式（5 位：分 时 日 月 周）。
            task_type: 任务类型。
            tool_name: 工具名称（task_type 为 tool_call 时必填）。
            tool_args: 工具参数。
            prompt: LLM 提示（task_type 为 llm_prompt 时必填）。
            description: 任务描述。
            max_retries: 最大重试次数。
            metadata: 扩展元数据。

        Returns:
            创建的任务信息。

        Raises:
            ValueError: 参数验证失败。
        """
        # 验证 Cron 表达式
        self._validate_cron_expr(cron_expr)

        # 验证任务配置
        task_config = self._validate_task_config(
            task_type=task_type,
            tool_name=tool_name,
            tool_args=tool_args,
            prompt=prompt,
        )

        # 检查名称唯一性
        self._check_name_unique(name)

        # 计算首次执行时间
        next_run_at = self._calculate_next_run_from_cron(cron_expr)

        # 创建任务
        task_id = str(uuid.uuid4())
        task = self._store.create_task(
            task_id=task_id,
            name=name,
            description=description,
            cron_expr=cron_expr,
            interval_seconds=None,
            one_shot=False,
            task_type=task_type.value,
            task_config=task_config.to_dict(),
            max_retries=max_retries or self._settings.scheduler_default_max_retries,
            next_run_at=next_run_at,
            metadata=metadata,
        )

        logger.info("定时任务已创建: name=%s, id=%s", name, task_id)
        return ScheduledTaskInfo.from_orm(task)

    def create_interval_task(
        self,
        *,
        name: str,
        interval_seconds: int,
        task_type: TaskType = TaskType.TOOL_CALL,
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
        prompt: str | None = None,
        description: str | None = None,
        max_retries: int | None = None,
        metadata: dict | None = None,
    ) -> ScheduledTaskInfo:
        """创建基于间隔的定时任务。

        Args:
            name: 任务名称（必须唯一）。
            interval_seconds: 执行间隔（秒）。
            task_type: 任务类型。
            tool_name: 工具名称。
            tool_args: 工具参数。
            prompt: LLM 提示。
            description: 任务描述。
            max_retries: 最大重试次数。
            metadata: 扩展元数据。

        Returns:
            创建的任务信息。

        Raises:
            ValueError: 参数验证失败。
        """
        # 验证间隔
        self._validate_interval(interval_seconds)

        # 验证任务配置
        task_config = self._validate_task_config(
            task_type=task_type,
            tool_name=tool_name,
            tool_args=tool_args,
            prompt=prompt,
        )

        # 检查名称唯一性
        self._check_name_unique(name)

        # 计算首次执行时间
        next_run_at = datetime.now() + timedelta(seconds=interval_seconds)

        # 创建任务
        task_id = str(uuid.uuid4())
        task = self._store.create_task(
            task_id=task_id,
            name=name,
            description=description,
            cron_expr=None,
            interval_seconds=interval_seconds,
            one_shot=False,
            task_type=task_type.value,
            task_config=task_config.to_dict(),
            max_retries=max_retries or self._settings.scheduler_default_max_retries,
            next_run_at=next_run_at,
            metadata=metadata,
        )

        logger.info("定时任务已创建: name=%s, id=%s", name, task_id)
        return ScheduledTaskInfo.from_orm(task)

    def create_one_shot_task(
        self,
        *,
        name: str,
        task_type: TaskType = TaskType.TOOL_CALL,
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
        prompt: str | None = None,
        description: str | None = None,
        metadata: dict | None = None,
    ) -> ScheduledTaskInfo:
        """创建一次性任务。

        Args:
            name: 任务名称。
            task_type: 任务类型。
            tool_name: 工具名称。
            tool_args: 工具参数。
            prompt: LLM 提示。
            description: 任务描述。
            metadata: 扩展元数据。

        Returns:
            创建的任务信息。

        Raises:
            ValueError: 参数验证失败。
        """
        # 验证任务配置
        task_config = self._validate_task_config(
            task_type=task_type,
            tool_name=tool_name,
            tool_args=tool_args,
            prompt=prompt,
        )

        # 检查名称唯一性
        self._check_name_unique(name)

        # 创建任务
        task_id = str(uuid.uuid4())
        task = self._store.create_task(
            task_id=task_id,
            name=name,
            description=description,
            cron_expr=None,
            interval_seconds=None,
            one_shot=True,
            task_type=task_type.value,
            task_config=task_config.to_dict(),
            max_retries=0,
            next_run_at=datetime.now(),
            metadata=metadata,
        )

        logger.info("一次性任务已创建: name=%s, id=%s", name, task_id)
        return ScheduledTaskInfo.from_orm(task)

    def get_task(self, task_id: str) -> ScheduledTaskInfo | None:
        """获取任务信息。"""
        task = self._store.get_task(task_id)
        if not task:
            return None
        return ScheduledTaskInfo.from_orm(task)

    def get_task_by_name(self, name: str) -> ScheduledTaskInfo | None:
        """按名称获取任务。"""
        task = self._store.get_task_by_name(name)
        if not task:
            return None
        return ScheduledTaskInfo.from_orm(task)

    def delete_task(self, task_id: str) -> bool:
        """删除任务。"""
        return self._store.delete_task(task_id)

    def list_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        enabled: bool | None = None,
        limit: int = 100,
    ) -> list[ScheduledTaskInfo]:
        """列出任务。"""
        tasks = self._store.list_tasks(
            status=status.value if status else None,
            enabled=enabled,
            limit=limit,
        )
        return [ScheduledTaskInfo.from_orm(t) for t in tasks]

    # ── 状态管理 ──────────────────────────────────────────────

    def enable_task(self, task_id: str) -> ScheduledTaskInfo | None:
        """启用任务。

        Args:
            task_id: 任务 ID。

        Returns:
            更新后的任务信息，如果任务不存在则返回 None。
        """
        task = self._store.get_task(task_id)
        if not task:
            return None

        # 检查是否可以启用
        if task.status not in (TaskStatus.DISABLED.value, TaskStatus.PAUSED.value):
            raise ValueError(f"任务状态 {task.status} 不允许启用")

        # 重新计算下次执行时间
        next_run_at = self._recalculate_next_run(task)

        updated = self._store.update_task_fields(
            task,
            enabled=True,
            status=TaskStatus.ACTIVE.value,
            next_run_at=next_run_at,
        )
        return ScheduledTaskInfo.from_orm(updated)

    def disable_task(self, task_id: str) -> ScheduledTaskInfo | None:
        """禁用任务。

        Args:
            task_id: 任务 ID。

        Returns:
            更新后的任务信息，如果任务不存在则返回 None。
        """
        task = self._store.get_task(task_id)
        if not task:
            return None

        updated = self._store.update_task_fields(
            task,
            enabled=False,
            status=TaskStatus.DISABLED.value,
        )
        return ScheduledTaskInfo.from_orm(updated)

    def pause_task(self, task_id: str) -> ScheduledTaskInfo | None:
        """暂停任务。

        Args:
            task_id: 任务 ID。

        Returns:
            更新后的任务信息，如果任务不存在则返回 None。
        """
        task = self._store.get_task(task_id)
        if not task:
            return None

        # 检查是否可以暂停
        if task.status != TaskStatus.ACTIVE.value:
            raise ValueError(f"任务状态 {task.status} 不允许暂停")

        updated = self._store.update_task_fields(
            task,
            status=TaskStatus.PAUSED.value,
        )
        return ScheduledTaskInfo.from_orm(updated)

    def resume_task(self, task_id: str) -> ScheduledTaskInfo | None:
        """恢复任务。

        Args:
            task_id: 任务 ID。

        Returns:
            更新后的任务信息，如果任务不存在则返回 None。
        """
        task = self._store.get_task(task_id)
        if not task:
            return None

        # 检查是否可以恢复
        if task.status != TaskStatus.PAUSED.value:
            raise ValueError(f"任务状态 {task.status} 不允许恢复")

        # 重新计算下次执行时间
        next_run_at = self._recalculate_next_run(task)

        updated = self._store.update_task_fields(
            task,
            status=TaskStatus.ACTIVE.value,
            next_run_at=next_run_at,
        )
        return ScheduledTaskInfo.from_orm(updated)

    # ── 执行统计 ──────────────────────────────────────────────

    def update_task_after_execution(
        self,
        task_id: str,
        *,
        success: bool,
    ) -> ScheduledTaskInfo | None:
        """任务执行后更新统计和状态。

        这是核心业务逻辑，处理：
        1. 执行统计更新
        2. 重试次数管理
        3. 状态转换（失败/完成）
        4. 计算下次执行时间

        Args:
            task_id: 任务 ID。
            success: 执行是否成功。

        Returns:
            更新后的任务信息，如果任务不存在则返回 None。
        """
        task = self._store.get_task(task_id)
        if not task:
            return None

        now = datetime.now()
        updates: dict[str, Any] = {
            "last_run_at": now,
            "total_runs": task.total_runs + 1,
        }

        # 更新成功/失败统计
        if success:
            updates["success_runs"] = task.success_runs + 1
            updates["retry_count"] = 0
        else:
            updates["failed_runs"] = task.failed_runs + 1
            updates["retry_count"] = task.retry_count + 1

        # 计算下次执行时间
        next_run_at = self._recalculate_next_run(task)
        if next_run_at:
            updates["next_run_at"] = next_run_at

        # 检查是否需要标记为失败（超过最大重试次数）
        if not success and task.retry_count + 1 >= task.max_retries:
            updates["status"] = TaskStatus.FAILED.value
            updates["enabled"] = False
            logger.warning(
                "任务达到最大重试次数，标记为失败: task_id=%s, retries=%d/%d",
                task_id,
                task.retry_count + 1,
                task.max_retries,
            )

        # 一次性任务完成后标记为完成
        if success and task.one_shot:
            updates["status"] = TaskStatus.COMPLETED.value
            updates["enabled"] = False
            updates["completed_at"] = now
            logger.info("一次性任务已完成: task_id=%s", task_id)

        # 更新任务
        updated = self._store.update_task_fields(task, **updates)
        return ScheduledTaskInfo.from_orm(updated)

    # ── 日志查询 ──────────────────────────────────────────────

    def get_task_logs(self, task_id: str, *, limit: int = 50) -> list[dict]:
        """获取任务执行日志。"""
        logs = self._store.get_task_logs(task_id, limit=limit)
        return [
            {
                "run_id": log.run_id,
                "status": log.status,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "finished_at": log.finished_at.isoformat() if log.finished_at else None,
                "duration_ms": log.duration_ms,
                "result_summary": log.result_summary,
                "error_type": log.error_type,
                "error_message": log.error_message,
            }
            for log in logs
        ]

    def get_stats(self) -> dict:
        """获取调度器统计信息。"""
        return {
            "scheduler_running": self._manager.is_running,
            "scheduler_enabled": self._settings.scheduler_enabled,
            **self._store.get_task_stats(),
        }

    # ── 内部验证方法 ──────────────────────────────────────────

    def _validate_cron_expr(self, cron_expr: str) -> None:
        """验证 Cron 表达式。

        Args:
            cron_expr: Cron 表达式。

        Raises:
            ValueError: 表达式无效。
        """
        if not cron_expr:
            raise ValueError("Cron 表达式不能为空")

        parts = cron_expr.strip().split()
        if len(parts) != 5:
            raise ValueError(
                f"无效的 Cron 表达式: {cron_expr}，需要 5 位（分 时 日 月 周）"
            )

        # 验证 croniter 能否解析
        try:
            croniter(cron_expr, datetime.now())
        except Exception as e:
            raise ValueError(f"无效的 Cron 表达式: {cron_expr}") from e

    def _validate_interval(self, interval_seconds: int) -> None:
        """验证间隔秒数。

        Args:
            interval_seconds: 间隔秒数。

        Raises:
            ValueError: 间隔无效。
        """
        if interval_seconds <= 0:
            raise ValueError(f"间隔秒数必须大于 0: {interval_seconds}")

    def _validate_task_config(
        self,
        *,
        task_type: TaskType,
        tool_name: str | None,
        tool_args: dict[str, Any] | None,
        prompt: str | None,
    ) -> TaskConfig:
        """验证任务配置。

        Args:
            task_type: 任务类型。
            tool_name: 工具名称。
            tool_args: 工具参数。
            prompt: LLM 提示。

        Returns:
            验证后的任务配置。

        Raises:
            ValueError: 配置无效。
        """
        if task_type == TaskType.TOOL_CALL:
            if not tool_name:
                raise ValueError("工具调用任务必须指定 tool_name")
        elif task_type == TaskType.LLM_PROMPT:
            if not prompt:
                raise ValueError("LLM 提示任务必须指定 prompt")
        elif task_type == TaskType.SYSTEM_EVENT:
            # 系统事件可以没有额外参数
            pass

        return TaskConfig(
            task_type=task_type,
            tool_name=tool_name,
            tool_args=tool_args or {},
            prompt=prompt,
        )

    def _check_name_unique(self, name: str) -> None:
        """检查任务名称唯一性。

        Args:
            name: 任务名称。

        Raises:
            ValueError: 名称已存在。
        """
        existing = self._store.get_task_by_name(name)
        if existing:
            raise ValueError(f"任务名称已存在: {name}")

    def _calculate_next_run_from_cron(self, cron_expr: str) -> datetime:
        """从 Cron 表达式计算下次执行时间。

        Args:
            cron_expr: Cron 表达式。

        Returns:
            下次执行时间。
        """
        try:
            cron = croniter(cron_expr, datetime.now())
            return cron.get_next(datetime)
        except Exception as e:
            raise ValueError(f"无法计算执行时间: {cron_expr}") from e

    def _recalculate_next_run(self, task: Any) -> datetime | None:
        """重新计算任务的下次执行时间。

        Args:
            task: 任务实例。

        Returns:
            下次执行时间，如果任务已完成则返回 None。
        """
        # 一次性任务不计算
        if task.one_shot:
            return None

        # 已完成或失败的任务不计算
        if task.status in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value):
            return None

        now = datetime.now()

        if task.cron_expr:
            try:
                cron = croniter(task.cron_expr, now)
                return cron.get_next(datetime)
            except Exception as e:
                logger.error(
                    "Cron 表达式解析失败: %s, error=%s", task.cron_expr, str(e)
                )
                return None

        elif task.interval_seconds:
            return now + timedelta(seconds=task.interval_seconds)

        return None
