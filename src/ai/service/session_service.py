"""会话管理服务 — 会话列表、详情、归档、删除。

共享服务层，CLI 和 API 路由统一使用。
"""

from __future__ import annotations

from src.ai.config.logging_setup import get_logger
from typing import Any

logger = get_logger(__name__)


class SessionService:
    """会话管理服务。

    职责：
    1. 列出会话
    2. 获取会话详情
    3. 归档会话
    4. 删除会话
    """

    def __init__(self, *, session_factory: Any) -> None:
        self._session_factory = session_factory

    def _get_session(self) -> Any:
        """创建数据库会话。"""
        return self._session_factory()

    def list_sessions(
        self,
        *,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """列出会话。

        Args:
            status: 按状态过滤（active/archived/deleted）。
            limit: 最大返回数量。

        Returns:
            会话信息列表。
        """
        from src.ai.storage.runtime_repository import ChatSessionRepository

        with self._get_session() as session:
            repo = ChatSessionRepository(session)
            sessions = repo.list(limit=limit)
            results = [self._session_to_dict(s) for s in sessions]
            if status:
                results = [s for s in results if s["status"] == status]
            return results

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """获取会话详情。

        Args:
            session_id: 会话 ID。

        Returns:
            会话信息字典，不存在返回 None。
        """
        from src.ai.storage.runtime_repository import ChatSessionRepository

        with self._get_session() as session:
            repo = ChatSessionRepository(session)
            chat_session = repo.get_by_session_id(session_id)
            if chat_session is None:
                return None
            return self._session_to_dict(chat_session)

    def archive_session(self, session_id: str) -> bool:
        """归档会话。

        Args:
            session_id: 会话 ID。

        Returns:
            是否归档成功。
        """
        from src.ai.storage.runtime_repository import ChatSessionRepository

        with self._get_session() as session:
            repo = ChatSessionRepository(session)
            chat_session = repo.get_by_session_id(session_id)
            if chat_session is None:
                return False
            repo.update(chat_session.id, status="archived")
            return True

    def delete_session(self, session_id: str) -> bool:
        """删除会话。

        Args:
            session_id: 会话 ID。

        Returns:
            是否删除成功。
        """
        from src.ai.storage.runtime_repository import ChatSessionRepository

        with self._get_session() as session:
            repo = ChatSessionRepository(session)
            chat_session = repo.get_by_session_id(session_id)
            if chat_session is None:
                return False
            repo.update(chat_session.id, status="deleted")
            return True

    @staticmethod
    def _session_to_dict(chat_session: Any) -> dict[str, Any]:
        """将 ChatSession 转换为字典。"""
        return {
            "session_id": chat_session.session_id,
            "title": chat_session.title,
            "current_model": chat_session.current_model,
            "status": chat_session.status,
            "message_count": chat_session.message_count,
            "created_at": str(chat_session.created_at),
            "last_active_at": str(chat_session.last_active_at),
        }
