"""定时任务数据仓库。"""

from datetime import datetime
from typing import Any

from sqlmodel import select

from src.ai.storage.base_repository import BaseRepository
from src.ai.storage.scheduler_models import ScheduledTask, TaskExecutionLog


class ScheduledTaskRepository(BaseRepository[ScheduledTask]):
    """定时任务仓库。"""

    model = ScheduledTask

    def get_active_tasks(self) -> list[ScheduledTask]:
        """获取所有活跃且启用的任务。"""
        return self.list(status="active", enabled=True, limit=1000)

    def get_due_tasks(self, *, now: datetime | None = None) -> list[ScheduledTask]:
        """获取所有到期应执行的任务。"""
        if now is None:
            now = datetime.now()
        stmt = (
            select(ScheduledTask)
            .where(ScheduledTask.status == "active")
            .where(ScheduledTask.enabled == True)  # noqa: E712
            .where(ScheduledTask.next_run_at <= now)
            .order_by(ScheduledTask.next_run_at.asc())
        )
        return list(self.session.exec(stmt).all())

    def get_by_name(self, name: str) -> ScheduledTask | None:
        """按名称获取任务。"""
        return self.get_by_field("name", name)

    def get_stats(self) -> dict[str, Any]:
        """获取任务统计信息。"""
        total = self.count()
        active = self.count(status="active", enabled=True)
        failed = self.count(status="failed")
        completed = self.count(status="completed")

        return {
            "total_tasks": total,
            "active_tasks": active,
            "failed_tasks": failed,
            "completed_tasks": completed,
        }


class TaskExecutionLogRepository(BaseRepository[TaskExecutionLog]):
    """任务执行日志仓库。"""

    model = TaskExecutionLog

    def get_by_task(self, task_id: str, *, limit: int = 50) -> list[TaskExecutionLog]:
        """获取指定任务的执行日志。"""
        return self.list(
            task_id=task_id, limit=limit, order_by="started_at", descending=True
        )

    def get_by_run_id(self, run_id: str) -> TaskExecutionLog | None:
        """按执行 ID 获取日志。"""
        return self.get_by_field("run_id", run_id)

    def get_recent_logs(self, *, limit: int = 100) -> list[TaskExecutionLog]:
        """获取最近的执行日志。"""
        return self.list(limit=limit, order_by="started_at", descending=True)

    def get_failed_logs(self, *, limit: int = 50) -> list[TaskExecutionLog]:
        """获取失败的执行日志。"""
        return self.list(
            status="failed", limit=limit, order_by="started_at", descending=True
        )

    def update_log_status(
        self,
        log: TaskExecutionLog,
        *,
        status: str,
        result_summary: str | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> TaskExecutionLog:
        """更新执行日志状态。"""
        now = datetime.now()
        updates: dict[str, Any] = {
            "status": status,
            "finished_at": now,
        }
        if log.started_at:
            updates["duration_ms"] = (now - log.started_at).total_seconds() * 1000
        if result_summary:
            updates["result_summary"] = result_summary
        if error_type:
            updates["error_type"] = error_type
        if error_message:
            updates["error_message"] = error_message

        return self.update(log, **updates)
