"""调度器 API 服务 — SchedulerService 的薄包装。

共享服务层，API 路由统一使用。
"""

from __future__ import annotations

from dataclasses import asdict
from src.ai.config.logging_setup import get_logger
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.ai.utils.thread_pool import ThreadPoolManager

logger = get_logger(__name__)


class SchedulerApiService:
    """调度器 API 服务。

    职责：
    1. 定时任务 CRUD（cron、间隔、一次性）
    2. 任务状态管理（启用、禁用、暂停、恢复）
    3. 执行日志查询
    4. 调度器生命周期控制
    """

    def __init__(
        self,
        *,
        scheduler_service: Any,
        thread_pool: ThreadPoolManager | None = None,
    ) -> None:
        self._svc = scheduler_service
        self._thread_pool = thread_pool

    def _get_pool(self) -> ThreadPoolManager:
        """获取线程池实例。"""
        if self._thread_pool is None:
            from src.ai.utils.thread_pool import get_thread_pool

            self._thread_pool = get_thread_pool()
        return self._thread_pool

    # ── 任务创建 ──────────────────────────────────────────────

    def create_cron_task(
        self,
        *,
        name: str,
        cron_expr: str,
        task_type: str = "tool_call",
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
        prompt: str | None = None,
        description: str | None = None,
        max_retries: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """创建 cron 定时任务。

        Args:
            name: 任务名称。
            cron_expr: Cron 表达式。
            task_type: 任务类型。
            tool_name: 工具名称。
            tool_args: 工具参数。
            prompt: LLM 提示词。
            description: 任务描述。
            max_retries: 最大重试次数。
            metadata: 扩展元数据。

        Returns:
            任务信息字典。
        """
        task_info = self._svc.create_cron_task(
            name=name,
            cron_expr=cron_expr,
            task_type=task_type,
            tool_name=tool_name,
            tool_args=tool_args or {},
            prompt=prompt,
            description=description,
            max_retries=max_retries or 3,
            metadata=metadata or {},
        )
        return asdict(task_info)

    def create_interval_task(
        self,
        *,
        name: str,
        interval_seconds: int,
        task_type: str = "tool_call",
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
        prompt: str | None = None,
        description: str | None = None,
        max_retries: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """创建间隔定时任务。"""
        task_info = self._svc.create_interval_task(
            name=name,
            interval_seconds=interval_seconds,
            task_type=task_type,
            tool_name=tool_name,
            tool_args=tool_args or {},
            prompt=prompt,
            description=description,
            max_retries=max_retries or 3,
            metadata=metadata or {},
        )
        return asdict(task_info)

    def create_one_shot_task(
        self,
        *,
        name: str,
        task_type: str = "tool_call",
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
        prompt: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """创建一次性任务。"""
        task_info = self._svc.create_one_shot_task(
            name=name,
            task_type=task_type,
            tool_name=tool_name,
            tool_args=tool_args or {},
            prompt=prompt,
            description=description,
            metadata=metadata or {},
        )
        return asdict(task_info)

    # ── 任务查询 ──────────────────────────────────────────────

    def list_tasks(
        self,
        *,
        status: str | None = None,
        enabled: bool | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """列出定时任务。"""
        tasks = self._svc.list_tasks()
        results = [asdict(t) for t in tasks]
        if status:
            results = [t for t in results if t.get("status") == status]
        if enabled is not None:
            results = [t for t in results if t.get("enabled") == enabled]
        return results[:limit]

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """获取指定任务。"""
        task = self._svc.get_task(task_id)
        if task is None:
            return None
        return asdict(task)

    def delete_task(self, task_id: str) -> bool:
        """删除任务。"""
        try:
            self._svc.delete_task(task_id)
            return True
        except Exception:
            return False

    # ── 状态管理 ──────────────────────────────────────────────

    def enable_task(self, task_id: str) -> dict[str, Any] | None:
        """启用任务。"""
        self._svc.enable_task(task_id)
        return self.get_task(task_id)

    def disable_task(self, task_id: str) -> dict[str, Any] | None:
        """禁用任务。"""
        self._svc.disable_task(task_id)
        return self.get_task(task_id)

    def pause_task(self, task_id: str) -> dict[str, Any] | None:
        """暂停任务。"""
        self._svc.pause_task(task_id)
        return self.get_task(task_id)

    def resume_task(self, task_id: str) -> dict[str, Any] | None:
        """恢复任务。"""
        self._svc.resume_task(task_id)
        return self.get_task(task_id)

    # ── 日志和统计 ────────────────────────────────────────────

    def get_task_logs(
        self,
        task_id: str,
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """获取任务执行日志。"""
        logs = self._svc.get_task_logs(task_id)
        results = [asdict(log) for log in logs]
        return results[:limit]

    def get_stats(self) -> dict[str, Any]:
        """获取调度器统计信息。"""
        return self._svc.get_stats()
