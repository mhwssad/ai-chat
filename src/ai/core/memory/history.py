"""对话历史管理 — SQL 主存储 + 文件系统备份。

SQL（LangChain SQLChatMessageHistory）是运行时主存储，
文件系统（FileHistoryStore）是离线备份，供压缩策略等场景读取。
"""

from __future__ import annotations

from src.ai.config.logging_setup import get_logger
from typing import TYPE_CHECKING

from sqlalchemy import Engine
from sqlmodel import Session

if TYPE_CHECKING:
    from langchain_core.chat_history import BaseChatMessageHistory
    from langchain_core.messages import BaseMessage

    from src.ai.core.memory.history_store import FileHistoryStore

logger = get_logger(__name__)

_SUMMARY_MAX_MESSAGES = 8
_SUMMARY_MAX_CONTENT = 120


class ChatHistoryManager:
    """对话历史管理器。

    双存储架构：
    - SQL（主）：运行时消息读写，通过 LangChain SQLChatMessageHistory
    - 文件（备）：JSONL 离线备份，供 context 压缩策略读取

    Args:
        file_store: 文件系统历史存储（备份）。
        table_name: SQL 表名。
        engine: SQLAlchemy 引擎。
        history_file_enabled: 是否启用文件系统备份。
    """

    def __init__(
        self,
        file_store: FileHistoryStore,
        *,
        table_name: str,
        engine: Engine,
        history_file_enabled: bool = True,
    ) -> None:
        self._engine = engine
        self._table_name = table_name
        self._file_store = file_store
        self._history_file_enabled = history_file_enabled

    def get_history(self, session_id: str) -> BaseChatMessageHistory:
        """获取指定会话的 SQL 消息历史对象。"""
        from langchain_community.chat_message_histories import SQLChatMessageHistory

        return SQLChatMessageHistory(
            session_id=session_id,
            connection=self._engine,
            table_name=self._table_name,
        )

    def add_message(self, session_id: str, message: BaseMessage) -> None:
        """添加一条消息到 SQL 主存储，异步写入文件备份。"""
        history = self.get_history(session_id)
        history.add_message(message)
        self._touch_session(session_id)

        if self._history_file_enabled:
            try:
                self._file_store.append_message(session_id, message)
            except Exception:
                logger.warning(
                    "文件备份写入失败（SQL 已成功）: session=%s",
                    session_id,
                    exc_info=True,
                )

    def get_messages(self, session_id: str) -> list[BaseMessage]:
        """从 SQL 主存储获取会话的所有消息。"""
        history = self.get_history(session_id)
        return history.messages

    def clear_history(self, session_id: str) -> None:
        """清空 SQL 主存储和文件备份。"""
        history = self.get_history(session_id)
        history.clear()
        self._touch_session(session_id, message_count=0)

        if self._history_file_enabled:
            try:
                self._file_store.clear(session_id)
            except Exception:
                logger.warning(
                    "文件备份清除失败（SQL 已清空）: session=%s",
                    session_id,
                    exc_info=True,
                )

    def message_count(self, session_id: str) -> int:
        """获取会话消息数量。"""
        return len(self.get_messages(session_id))

    def list_session_ids(self) -> list[str]:
        """从 SQL 中列出所有存在消息的会话 ID。

        Returns:
            不重复的 session_id 列表。
        """
        from sqlalchemy import text

        with self._engine.connect() as conn:
            result = conn.execute(
                text(
                    f"SELECT DISTINCT session_id FROM {self._table_name} "
                    f"ORDER BY session_id"
                )
            )
            return [row[0] for row in result.fetchall()]

    def get_session_summary(self, session_id: str) -> dict[str, object]:
        """获取会话历史摘要，供 API 查询。"""
        messages = self.get_messages(session_id)
        role_counts: dict[str, int] = {}
        for msg in messages:
            msg_type = getattr(msg, "type", "unknown")
            role_counts[msg_type] = role_counts.get(msg_type, 0) + 1

        recent: list[dict[str, str]] = []
        for msg in messages[-_SUMMARY_MAX_MESSAGES:]:
            content = str(getattr(msg, "content", ""))
            recent.append(
                {
                    "role": getattr(msg, "type", "unknown"),
                    "content": _summarize_content(content),
                }
            )

        return {
            "session_id": session_id,
            "message_count": len(messages),
            "role_counts": role_counts,
            "recent_messages": recent,
            "history_file_enabled": self._history_file_enabled,
        }

    def _touch_session(
        self, session_id: str, *, message_count: int | None = None
    ) -> None:
        """同步会话摘要表。"""
        try:
            from src.ai.storage.runtime_repository import ChatSessionRepository

            count = self.message_count(session_id) if message_count is None else message_count
            with Session(self._engine) as session:
                ChatSessionRepository(session).touch(
                    session_id,
                    message_count=count,
                )
                session.commit()
        except Exception:
            logger.debug("同步会话摘要失败: session=%s", session_id, exc_info=True)


def _summarize_content(content: str) -> str:
    """生成历史消息短摘要。"""
    normalized = " ".join(content.split())
    if len(normalized) <= _SUMMARY_MAX_CONTENT:
        return normalized
    return normalized[:_SUMMARY_MAX_CONTENT] + "..."
