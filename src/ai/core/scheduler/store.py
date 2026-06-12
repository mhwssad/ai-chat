"""定时任务持久化存储。"""

from __future__ import annotations

from src.ai.config.logging_setup import get_logger
from datetime import datetime
from typing import TYPE_CHECKING

from src.ai.storage.scheduler_models import ScheduledTask, TaskExecutionLog
from src.ai.storage.scheduler_repository import (
    ScheduledTaskRepository,
    TaskExecutionLogRepository,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

logger = get_logger(__name__)


class SchedulerStore:
    """定时任务持久化存储。

    封装数据库操作，提供定时任务和执行日志的 CRUD 接口。
    """

    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def _get_task_repo(self) -> ScheduledTaskRepository:
        """获取任务仓库实例。"""

        session = self._session_factory()
        return ScheduledTaskRepository(session)

    def _get_log_repo(self) -> TaskExecutionLogRepository:
        """获取日志仓库实例。"""

        session = self._session_factory()
        return TaskExecutionLogRepository(session)

    # ── 任务操作 ──────────────────────────────────────────────

    def create_task(
        self,
        *,
        task_id: str,
        name: str,
        description: str | None,
        cron_expr: str | None,
        interval_seconds: int | None,
        one_shot: bool,
        task_type: str,
        task_config: dict,
        max_retries: int,
        next_run_at: datetime,
        metadata: dict | None = None,
    ) -> ScheduledTask:
        """创建定时任务。"""
        repo = self._get_task_repo()
        task = repo.create(
            id=task_id,
            name=name,
            description=description,
            cron_expr=cron_expr,
            interval_seconds=interval_seconds,
            one_shot=one_shot,
            task_type=task_type,
            max_retries=max_retries,
            next_run_at=next_run_at,
        )
        task.set_task_config(task_config)
        if metadata:
            task.set_metadata(metadata)
        repo.save(task)
        logger.info("定时任务已创建: %s (%s)", name, task_id)
        return task

    def get_task(self, task_id: str) -> ScheduledTask | None:
        """获取任务。"""
        repo = self._get_task_repo()
        return repo.get_by_id(task_id)

    def get_task_by_name(self, name: str) -> ScheduledTask | None:
        """按名称获取任务。"""
        repo = self._get_task_repo()
        return repo.get_by_name(name)

    def update_task(self, task: ScheduledTask, **kwargs) -> ScheduledTask:
        """更新任务。"""
        repo = self._get_task_repo()
        return repo.update(task, **kwargs)

    def delete_task(self, task_id: str) -> bool:
        """删除任务。"""
        repo = self._get_task_repo()
        return repo.delete_by_id(task_id)

    def list_tasks(
        self,
        *,
        status: str | None = None,
        enabled: bool | None = None,
        limit: int = 100,
    ) -> list[ScheduledTask]:
        """列出任务。"""
        repo = self._get_task_repo()
        filters: dict = {}
        if status:
            filters["status"] = status
        if enabled is not None:
            filters["enabled"] = enabled
        return repo.list(limit=limit, **filters)

    def get_active_tasks(self) -> list[ScheduledTask]:
        """获取所有活跃任务。"""
        repo = self._get_task_repo()
        return repo.get_active_tasks()

    def get_due_tasks(self, now: datetime | None = None) -> list[ScheduledTask]:
        """获取到期任务。"""
        repo = self._get_task_repo()
        return repo.get_due_tasks(now=now)

    def update_task_fields(
        self,
        task: ScheduledTask,
        **kwargs,
    ) -> ScheduledTask:
        """更新任务字段（纯数据操作）。

        Args:
            task: 任务实例。
            **kwargs: 要更新的字段。

        Returns:
            更新后的任务。
        """
        repo = self._get_task_repo()
        return repo.update(task, **kwargs)

    def get_task_stats(self) -> dict:
        """获取任务统计。"""
        repo = self._get_task_repo()
        return repo.get_stats()

    # ── 执行日志操作 ──────────────────────────────────────────

    def create_execution_log(
        self,
        *,
        task_id: str,
        run_id: str,
        session_id: str | None = None,
    ) -> TaskExecutionLog:
        """创建执行日志。"""
        repo = self._get_log_repo()
        log = repo.create(
            task_id=task_id,
            run_id=run_id,
            session_id=session_id,
        )
        return log

    def get_execution_log(self, run_id: str) -> TaskExecutionLog | None:
        """获取执行日志。"""
        repo = self._get_log_repo()
        return repo.get_by_run_id(run_id)

    def update_execution_log(
        self,
        log: TaskExecutionLog,
        *,
        status: str,
        result_summary: str | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> TaskExecutionLog:
        """更新执行日志。"""
        repo = self._get_log_repo()
        return repo.update_log_status(
            log,
            status=status,
            result_summary=result_summary,
            error_type=error_type,
            error_message=error_message,
        )

    def get_task_logs(self, task_id: str, *, limit: int = 50) -> list[TaskExecutionLog]:
        """获取任务执行日志。"""
        repo = self._get_log_repo()
        return repo.get_by_task(task_id, limit=limit)

    def get_recent_logs(self, *, limit: int = 100) -> list[TaskExecutionLog]:
        """获取最近的执行日志。"""
        repo = self._get_log_repo()
        return repo.get_recent_logs(limit=limit)

    def cleanup_old_logs(self, days: int = 30) -> int:
        """清理旧的执行日志。"""
        repo = self._get_log_repo()
        cutoff = datetime.now().timestamp() - (days * 86400)
        cutoff_dt = datetime.fromtimestamp(cutoff)

        # 获取所有日志
        all_logs = repo.list(limit=10000)
        deleted = 0
        for log in all_logs:
            if log.started_at and log.started_at < cutoff_dt:
                repo.delete(log)
                deleted += 1

        if deleted > 0:
            logger.info("已清理 %d 条过期执行日志", deleted)
        return deleted
