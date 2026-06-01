"""Agent checkpoint 管理 — 封装 LangGraph Checkpointer 的查询、删除等操作。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CheckpointInfo:
    """Checkpoint 摘要信息。"""

    thread_id: str
    checkpoint_id: str
    created_at: str
    status: str  # "active" | "completed" | "error"
    iteration: int
    message_count: int


class CheckpointManager:
    """Checkpoint 管理器。

    封装 LangGraph Checkpointer 的查询、删除、列表等管理操作。

    Args:
        checkpointer: LangGraph AsyncCheckpointer 实例。
    """

    def __init__(self, checkpointer: Any) -> None:
        self._checkpointer = checkpointer

    async def list_checkpoints(
        self,
        thread_id: str | None = None,
        *,
        limit: int = 20,
    ) -> list[CheckpointInfo]:
        """列出 checkpoint。

        Args:
            thread_id: 过滤指定线程 ID，None 表示全部。
            limit: 最大返回数量。

        Returns:
            Checkpoint 摘要列表。
        """
        try:
            config = {"configurable": {"thread_id": thread_id or "*"}}
            checkpoints = []
            async for cp in self._checkpointer.alist(config, limit=limit):
                state = cp.checkpoint
                messages = state.get("messages", [])
                checkpoints.append(
                    CheckpointInfo(
                        thread_id=cp.config.get("configurable", {}).get(
                            "thread_id", ""
                        ),
                        checkpoint_id=cp.id,
                        created_at=str(cp.metadata.get("created_at", "")),
                        status=self._determine_status(state),
                        iteration=state.get("iteration", 0),
                        message_count=len(messages)
                        if isinstance(messages, list)
                        else 0,
                    )
                )
            return checkpoints
        except Exception:
            logger.warning("列出 checkpoint 失败", exc_info=True)
            return []

    async def get_checkpoint(self, thread_id: str) -> dict[str, Any] | None:
        """获取指定线程的最新 checkpoint 状态。

        Args:
            thread_id: 线程 ID。

        Returns:
            状态字典，不存在返回 None。
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}
            cp = await self._checkpointer.aget(config)
            if cp is None:
                return None
            return cp.checkpoint
        except Exception:
            logger.warning("获取 checkpoint 失败: thread=%s", thread_id, exc_info=True)
            return None

    async def delete_checkpoint(self, thread_id: str) -> bool:
        """删除指定线程的所有 checkpoint。

        Args:
            thread_id: 线程 ID。

        Returns:
            True 表示成功删除。
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}
            # LangGraph 的 delete 需要具体 config，这里遍历删除
            async for cp in self._checkpointer.alist(config):
                await self._checkpointer.adelete(cp.config)
            return True
        except Exception:
            logger.warning("删除 checkpoint 失败: thread=%s", thread_id, exc_info=True)
            return False

    @staticmethod
    def _determine_status(state: dict[str, Any]) -> str:
        """从状态确定 checkpoint 状态。"""
        if state.get("error"):
            return "error"
        if state.get("is_plan_mode"):
            return "active"
        if state.get("iteration", 0) >= state.get("max_iterations", 10):
            return "completed"
        return "active"
