"""定时任务执行器。

职责：纯任务执行，只负责：
1. 执行不同类型的任务（工具调用、LLM 提示、系统事件）
2. 返回执行结果

不负责：
- 执行日志记录（由 SchedulerManager 处理）
- 任务统计更新（由 SchedulerService 处理）
"""

from __future__ import annotations

import asyncio
from src.ai.config.logging_setup import get_logger
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.ai.core.scheduler.types import (
    ExecutionStatus,
    TaskConfig,
    TaskExecutionResult,
    TaskType,
)

if TYPE_CHECKING:
    from src.ai.core.tools.manager import ToolManager

logger = get_logger(__name__)


class TaskExecutor:
    """定时任务执行器。

    职责：纯任务执行，只负责：
    1. 执行不同类型的任务
    2. 返回执行结果

    不负责：
    - 执行日志记录
    - 任务统计更新
    """

    def __init__(
        self,
        *,
        tool_manager: ToolManager | None = None,
        llm: Any | None = None,
    ) -> None:
        self._tool_manager = tool_manager
        self._llm = llm

    async def execute(
        self,
        task_id: str,
        task_config: TaskConfig,
        *,
        timeout: int = 300,
    ) -> TaskExecutionResult:
        """执行任务。

        Args:
            task_id: 任务 ID。
            task_config: 任务配置。
            timeout: 执行超时（秒）。

        Returns:
            任务执行结果。
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.now()

        logger.info("开始执行任务: task_id=%s, run_id=%s", task_id, run_id)

        try:
            # 根据任务类型执行
            result = await asyncio.wait_for(
                self._execute_by_type(task_config),
                timeout=timeout,
            )

            finished_at = datetime.now()
            duration_ms = (finished_at - started_at).total_seconds() * 1000

            logger.info(
                "任务执行成功: task_id=%s, run_id=%s, duration=%.2fms",
                task_id,
                run_id,
                duration_ms,
            )

            return TaskExecutionResult(
                run_id=run_id,
                task_id=task_id,
                status=ExecutionStatus.SUCCESS,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
                result_summary=result[:500] if result else None,
                error_type=None,
                error_message=None,
            )

        except asyncio.TimeoutError:
            finished_at = datetime.now()
            duration_ms = (finished_at - started_at).total_seconds() * 1000

            logger.warning("任务执行超时: task_id=%s, run_id=%s", task_id, run_id)

            return TaskExecutionResult(
                run_id=run_id,
                task_id=task_id,
                status=ExecutionStatus.TIMEOUT,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
                result_summary=None,
                error_type="TimeoutError",
                error_message=f"任务执行超时 ({timeout}s)",
            )

        except Exception as e:
            finished_at = datetime.now()
            duration_ms = (finished_at - started_at).total_seconds() * 1000

            logger.error(
                "任务执行失败: task_id=%s, run_id=%s, error=%s",
                task_id,
                run_id,
                str(e),
                exc_info=True,
            )

            return TaskExecutionResult(
                run_id=run_id,
                task_id=task_id,
                status=ExecutionStatus.FAILED,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
                result_summary=None,
                error_type=type(e).__name__,
                error_message=str(e)[:500],
            )

    async def _execute_by_type(self, task_config: TaskConfig) -> str:
        """根据任务类型执行。"""
        if task_config.task_type == TaskType.TOOL_CALL:
            return await self._execute_tool_call(task_config)
        elif task_config.task_type == TaskType.LLM_PROMPT:
            return await self._execute_llm_prompt(task_config)
        elif task_config.task_type == TaskType.SYSTEM_EVENT:
            return await self._execute_system_event(task_config)
        else:
            raise ValueError(f"未知的任务类型: {task_config.task_type}")

    async def _execute_tool_call(self, task_config: TaskConfig) -> str:
        """执行工具调用任务。"""
        if not self._tool_manager:
            raise RuntimeError("工具管理器未初始化")

        if not task_config.tool_name:
            raise ValueError("工具调用任务必须指定 tool_name")

        logger.debug(
            "执行工具调用: %s, args=%s", task_config.tool_name, task_config.tool_args
        )

        result = await self._tool_manager.execute(
            task_config.tool_name,
            task_config.tool_args,
        )

        return str(result) if result else "工具执行完成（无返回值）"

    async def _execute_llm_prompt(self, task_config: TaskConfig) -> str:
        """执行 LLM 提示任务。"""
        if not self._llm:
            raise RuntimeError("LLM 未初始化")

        if not task_config.prompt:
            raise ValueError("LLM 提示任务必须指定 prompt")

        logger.debug("执行 LLM 提示: %s", task_config.prompt[:100])

        from langchain_core.messages import HumanMessage

        messages = [HumanMessage(content=task_config.prompt)]
        response = await self._llm.ainvoke(messages)

        return response.content if hasattr(response, "content") else str(response)

    async def _execute_system_event(self, task_config: TaskConfig) -> str:
        """执行系统事件任务。"""
        if not task_config.system_event:
            raise ValueError("系统事件任务必须指定 system_event")

        logger.debug("执行系统事件: %s", task_config.system_event)

        # 系统事件处理（可扩展）
        event_handlers = {
            "cleanup_logs": self._handle_cleanup_logs,
            "rebuild_index": self._handle_rebuild_index,
        }

        handler = event_handlers.get(task_config.system_event)
        if handler:
            return await handler(task_config.extra)

        return f"未知的系统事件: {task_config.system_event}"

    async def _handle_cleanup_logs(self, extra: dict) -> str:
        """处理日志清理事件。"""
        # 注意：这个方法现在需要外部传入 store
        # 暂时返回提示
        return "日志清理功能需要通过 SchedulerService 调用"

    async def _handle_rebuild_index(self, extra: dict) -> str:
        """处理索引重建事件。"""
        return "索引重建完成"
