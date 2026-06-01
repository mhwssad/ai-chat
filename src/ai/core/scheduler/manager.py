"""定时任务调度管理器。

职责：纯调度引擎，只负责调度循环和任务执行触发。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from croniter import croniter

from src.ai.core.scheduler.executor import TaskExecutor
from src.ai.core.scheduler.store import SchedulerStore
from src.ai.core.scheduler.types import TaskConfig

if TYPE_CHECKING:
    from src.ai.config.settings import SchedulerSettings

logger = logging.getLogger(__name__)


class SchedulerManager:
    """定时任务调度管理器。

    职责：纯调度引擎，只负责：
    1. 调度循环（检查到期任务、触发执行）
    2. 生命周期管理（启动/停止）
    3. 计算下次执行时间

    不负责：
    - 任务 CRUD 操作（由 SchedulerService 处理）
    - 状态管理（由 SchedulerService 处理）
    - 业务逻辑（由 SchedulerService 处理）
    """

    def __init__(
        self,
        *,
        settings: SchedulerSettings,
        store: SchedulerStore,
        tool_manager: Any | None = None,
        llm: Any | None = None,
    ) -> None:
        self._settings = settings
        self._store = store
        self._executor = TaskExecutor(
            tool_manager=tool_manager,
            llm=llm,
        )
        # service 回调，用于更新任务统计
        self._on_task_executed: Any | None = None

    def set_task_executed_callback(self, callback: Any) -> None:
        """设置任务执行完成回调。

        Args:
            callback: 回调函数，签名：(task_id: str, success: bool) -> None
        """
        self._on_task_executed = callback

        # 调度循环状态
        self._running = False
        self._task: asyncio.Task | None = None
        self._semaphore: asyncio.Semaphore | None = None

    @property
    def is_running(self) -> bool:
        """调度器是否正在运行。"""
        return self._running

    async def start(self) -> None:
        """启动调度器。"""
        if self._running:
            logger.warning("调度器已在运行中")
            return

        if not self._settings.scheduler_enabled:
            logger.info("定时任务调度器已禁用")
            return

        self._running = True
        self._semaphore = asyncio.Semaphore(self._settings.scheduler_max_concurrent)

        # 启动调度循环
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info(
            "定时任务调度器已启动 (check_interval=%ds, max_concurrent=%d)",
            self._settings.scheduler_check_interval,
            self._settings.scheduler_max_concurrent,
        )

    async def stop(self) -> None:
        """停止调度器。"""
        if not self._running:
            return

        self._running = False

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._task = None
        logger.info("定时任务调度器已停止")

    async def _scheduler_loop(self) -> None:
        """调度主循环。"""
        logger.debug("调度循环已启动")

        while self._running:
            try:
                await self._check_and_execute_tasks()
                await self._cleanup_old_logs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("调度循环异常: %s", str(e), exc_info=True)

            # 等待下一次检查
            try:
                await asyncio.sleep(self._settings.scheduler_check_interval)
            except asyncio.CancelledError:
                break

        logger.debug("调度循环已退出")

    async def _check_and_execute_tasks(self) -> None:
        """检查并执行到期任务。"""
        now = datetime.now()
        due_tasks = self._store.get_due_tasks(now)

        if not due_tasks:
            return

        logger.debug("发现 %d 个到期任务", len(due_tasks))

        for task in due_tasks:
            if not self._running:
                break

            # 使用信号量控制并发
            async with self._semaphore:
                await self._execute_task(task)

    async def _execute_task(self, task: Any) -> None:
        """执行单个任务。"""
        import uuid

        task_config = TaskConfig.from_dict(task.get_task_config())
        run_id = str(uuid.uuid4())

        # 创建执行日志
        log = self._store.create_execution_log(
            task_id=task.id,
            run_id=run_id,
        )

        # 执行任务
        result = await self._executor.execute(
            task.id,
            task_config,
            timeout=self._settings.scheduler_task_timeout,
        )

        # 更新执行日志
        self._store.update_execution_log(
            log,
            status=result.status.value,
            result_summary=result.result_summary,
            error_type=result.error_type,
            error_message=result.error_message,
        )

        # 通知 service 更新任务统计（通过回调）
        if self._on_task_executed:
            try:
                self._on_task_executed(task.id, result.status.value == "success")
            except Exception as e:
                logger.error("更新任务统计失败: task_id=%s, error=%s", task.id, str(e))

        logger.debug(
            "任务执行完成: task_id=%s, run_id=%s, status=%s",
            task.id,
            run_id,
            result.status.value,
        )

    def calculate_next_run(self, task: Any) -> datetime | None:
        """计算任务下次执行时间。

        Args:
            task: 任务实例（ORM 对象）。

        Returns:
            下次执行时间，如果任务已完成则返回 None。
        """
        if task.one_shot:
            return None

        now = datetime.now()

        if task.cron_expr:
            # 使用 croniter 计算下次执行时间
            try:
                cron = croniter(task.cron_expr, now)
                return cron.get_next(datetime)
            except Exception as e:
                logger.error(
                    "Cron 表达式解析失败: %s, error=%s", task.cron_expr, str(e)
                )
                return None

        elif task.interval_seconds:
            # 间隔模式
            return now + timedelta(seconds=task.interval_seconds)

        return None

    async def _cleanup_old_logs(self) -> None:
        """定期清理旧日志。"""
        # 每天只执行一次清理
        now = datetime.now()
        if now.hour == 0 and now.minute < self._settings.scheduler_check_interval:
            self._store.cleanup_old_logs(self._settings.scheduler_cleanup_days)
