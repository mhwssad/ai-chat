"""会话管理服务 — 会话列表、详情、归档、删除。

共享服务层，API 路由统一使用。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from src.ai.config.logging_setup import get_logger
from typing import Any

from src.ai.config.base_config import project_root

logger = get_logger(__name__)


class SessionService:
    """会话管理服务。

    职责：
    1. 创建会话
    2. 列出会话
    3. 获取会话详情
    4. 归档会话
    5. 删除会话（硬删除，清理所有关联数据）
    """

    def __init__(
        self,
        *,
        session_factory: Any,
        chat_history_manager: Any = None,
        settings: Any = None,
    ) -> None:
        self._session_factory = session_factory
        self._chat_history_manager = chat_history_manager
        self._settings = settings

    def _get_session(self) -> Any:
        """创建数据库会话。"""
        return self._session_factory()

    # ── SQL 表硬删除 ───────────────────────────────────────

    _SESSION_TABLES = [
        "chat_message_store",
        "model_calls",
        "tool_calls",
        "memory_entries",
        "audit_logs",
    ]

    def _hard_delete_sql_records(self, db_session: Any, session_id: str) -> int:
        """删除所有 SQL 表中与 session_id 关联的记录。

        Args:
            db_session: SQLAlchemy Session。
            session_id: 会话 ID。

        Returns:
            删除的总行数。
        """
        from sqlalchemy import text

        total = 0
        for table in self._SESSION_TABLES:
            try:
                result = db_session.execute(
                    text(f"DELETE FROM {table} WHERE session_id = :sid"),
                    {"sid": session_id},
                )
                total += result.rowcount
            except Exception:
                logger.debug("清理表 %s 失败", table, exc_info=True)

        # 物理删除 chat_sessions 记录
        try:
            result = db_session.execute(
                text("DELETE FROM chat_sessions WHERE session_id = :sid"),
                {"sid": session_id},
            )
            total += result.rowcount
        except Exception:
            logger.debug("清理 chat_sessions 失败", exc_info=True)

        db_session.commit()
        return total

    # ── 文件清理 ──────────────────────────────────────────

    def _cleanup_session_files(self, session_id: str) -> None:
        """清理会话关联的磁盘文件：历史记录 + 记忆文件。"""
        if self._settings is None:
            return

        base_dir = project_root / self._settings.memory.memory_dir

        # 清理历史记录会话目录: {base_dir}/sessions/{session_id}/
        history_dir = base_dir / "sessions" / session_id
        if history_dir.exists():
            try:
                shutil.rmtree(history_dir)
                logger.debug("已清理历史目录: %s", history_dir)
            except Exception:
                logger.warning("清理历史目录失败: %s", history_dir, exc_info=True)

        # 清理记忆文件: {base_dir}/sessions/{session_id}.md
        memory_file = base_dir / "sessions" / f"{session_id}.md"
        if memory_file.exists():
            try:
                memory_file.unlink()
                logger.debug("已清理记忆文件: %s", memory_file)
            except Exception:
                logger.warning("清理记忆文件失败: %s", memory_file, exc_info=True)

    # ── CRUD ───────────────────────────────────────────────

    def create_session(
        self,
        *,
        session_id: str | None = None,
        title: str | None = None,
        current_model: str | None = None,
    ) -> dict[str, Any]:
        """创建新会话。

        Args:
            session_id: 会话 ID，不传则自动生成 UUID。
            title: 会话标题。
            current_model: 当前使用的模型。

        Returns:
            创建的会话信息字典。

        Raises:
            ValueError: session_id 已存在时抛出。
        """
        import uuid

        from src.ai.storage.runtime_repository import ChatSessionRepository

        sid = session_id or str(uuid.uuid4())
        logger.info("[session] create session_id=%s title=%s", sid, title)
        with self._get_session() as session:
            repo = ChatSessionRepository(session)
            existing = repo.get_by_session_id(sid)
            if existing is not None:
                raise ValueError(f"会话 ID 已存在: {sid}")
            chat_session = repo.create(
                session_id=sid,
                title=title,
                current_model=current_model,
            )
            session.commit()
            return self._session_to_dict(chat_session)

    def list_sessions(
        self,
        *,
        status: str | None = "active",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """列出会话。

        Args:
            status: 按状态过滤（active/archived/deleted），默认 "active"。
            limit: 最大返回数量。

        Returns:
            会话信息列表。
        """
        from src.ai.storage.runtime_repository import ChatSessionRepository

        with self._get_session() as session:
            repo = ChatSessionRepository(session)
            sessions = repo.list(limit=limit)
            results = [self._session_to_dict(s) for s in sessions]
            if status is not None:
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
            repo.update(chat_session, status="archived")
            session.commit()
            return True

    def delete_session(self, session_id: str) -> bool:
        """硬删除会话 — 彻底清理所有关联数据。

        清理范围：
        - SQL 表: chat_message_store, model_calls, tool_calls,
          memory_entries, audit_logs, chat_sessions
        - 磁盘文件: 对话历史 JSONL + 记忆 .md 文件

        Args:
            session_id: 会话 ID。

        Returns:
            是否删除成功。
        """
        # 1. 先清理 ChatHistoryManager 的 SQL 消息历史（避免与硬删除冲突）
        if self._chat_history_manager is not None:
            try:
                self._chat_history_manager.clear_history(session_id)
            except Exception:
                logger.warning("清理对话历史失败: %s", session_id, exc_info=True)

        # 2. 硬删除所有 SQL 关联记录
        deleted_rows = 0
        with self._get_session() as session:
            deleted_rows = self._hard_delete_sql_records(session, session_id)

        # 3. 清理磁盘文件
        self._cleanup_session_files(session_id)

        logger.info(
            "[session] delete session_id=%s deleted_rows=%d",
            session_id, deleted_rows,
        )
        return deleted_rows > 0

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
