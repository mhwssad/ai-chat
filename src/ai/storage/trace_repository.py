"""Agent 执行追踪 Repository。"""

from __future__ import annotations

from src.ai.storage.base_repository import BaseRepository
from src.ai.storage.trace_models import AgentTrace, AgentTraceStepRecord


class TraceRepository(BaseRepository[AgentTrace]):
    """Agent 追踪主表仓库。"""

    model = AgentTrace

    def list_by_session(
        self, session_id: str, *, limit: int = 20
    ) -> list[AgentTrace]:
        """按会话 ID 查询追踪列表（最新在前）。

        Args:
            session_id: 会话 ID。
            limit: 最大返回数。

        Returns:
            追踪记录列表。
        """
        return self.list(
            filters={"session_id": session_id},
            order_by="started_at",
            order_desc=True,
            limit=limit,
        )


class TraceStepRepository(BaseRepository[AgentTraceStepRecord]):
    """Agent 追踪步骤仓库。"""

    model = AgentTraceStepRecord

    def list_by_trace(self, trace_id: str) -> list[AgentTraceStepRecord]:
        """按追踪 ID 查询所有步骤。

        Args:
            trace_id: 追踪 ID。

        Returns:
            步骤列表（按序号排序）。
        """
        return self.list(
            filters={"trace_id": trace_id},
            order_by="step_index",
            order_desc=False,
            limit=200,
        )
