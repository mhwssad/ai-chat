"""Agent 执行链路追踪记录器。

职责：
1. 每次请求生成唯一 trace_id
2. 记录每个步骤：推理→工具选择→参数构造→执行→结果→下一步推理
3. 结构化存储到 DB
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.ai.config.logging_setup import get_logger

if TYPE_CHECKING:
    from src.ai.storage.database import SessionFactory

logger = get_logger(__name__)


@dataclass
class StepRecord:
    """内存中的步骤记录（批量写入前暂存）。"""

    step_index: int
    step_type: str
    title: str = ""
    input_summary: str | None = None
    output_summary: str | None = None
    duration_ms: int = 0
    status: str = "success"
    error: str | None = None


class TraceRecorder:
    """执行链路追踪记录器。

    在 Agent 执行期间收集步骤，执行完成后批量写入 DB。

    Args:
        session_id: 关联的会话 ID。
        session_factory: 数据库 session 工厂。
    """

    def __init__(
        self,
        *,
        session_id: str,
        session_factory: SessionFactory,
    ) -> None:
        self._trace_id = uuid.uuid4().hex[:16]
        self._session_id = session_id
        self._session_factory = session_factory
        self._steps: list[StepRecord] = []
        self._start_time = time.perf_counter()
        self._total_tokens = 0

    @property
    def trace_id(self) -> str:
        """当前追踪 ID。"""
        return self._trace_id

    def record_step(
        self,
        *,
        step_type: str,
        title: str = "",
        input_summary: str | None = None,
        output_summary: str | None = None,
        duration_ms: int = 0,
        status: str = "success",
        error: str | None = None,
    ) -> None:
        """记录一个执行步骤。

        Args:
            step_type: 步骤类型（llm / tool / reflection / context 等）。
            title: 步骤标题。
            input_summary: 输入摘要。
            output_summary: 输出摘要。
            duration_ms: 步骤耗时。
            status: 步骤状态。
            error: 错误信息。
        """
        self._steps.append(
            StepRecord(
                step_index=len(self._steps) + 1,
                step_type=step_type,
                title=title,
                input_summary=input_summary,
                output_summary=output_summary,
                duration_ms=duration_ms,
                status=status,
                error=error,
            )
        )

    def add_tokens(self, tokens: int) -> None:
        """累加 token 使用量。"""
        self._total_tokens += tokens

    def finish(
        self,
        *,
        status: str = "completed",
        error_message: str | None = None,
    ) -> str:
        """完成追踪，批量写入 DB。

        Args:
            status: 最终状态。
            error_message: 错误消息（如果失败）。

        Returns:
            trace_id。
        """
        from src.ai.storage.trace_repository import (
            TraceRepository,
            TraceStepRepository,
        )
        from src.ai.storage.utils import dt_now

        total_duration = int((time.perf_counter() - self._start_time) * 1000)

        try:
            with self._session_factory() as session:
                # 写入主记录
                trace_repo = TraceRepository(session)
                trace_repo.create(
                    trace_id=self._trace_id,
                    session_id=self._session_id,
                    status=status,
                    total_steps=len(self._steps),
                    total_tokens=self._total_tokens,
                    total_duration_ms=total_duration,
                    started_at=dt_now(),
                    finished_at=dt_now(),
                    error_message=error_message,
                )

                # 批量写入步骤
                step_repo = TraceStepRepository(session)
                for step in self._steps:
                    step_repo.create(
                        trace_id=self._trace_id,
                        step_index=step.step_index,
                        step_type=step.step_type,
                        title=step.title,
                        input_summary=step.input_summary,
                        output_summary=step.output_summary,
                        duration_ms=step.duration_ms,
                        status=step.status,
                        error=step.error,
                    )

                session.commit()
                logger.info(
                    "追踪记录已保存: trace_id=%s, steps=%d, duration=%dms",
                    self._trace_id,
                    len(self._steps),
                    total_duration,
                )
        except Exception:
            logger.exception("追踪记录保存失败: trace_id=%s", self._trace_id)

        return self._trace_id
