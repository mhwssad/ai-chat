"""对话历史管理 — SQL 主存储 + 文件系统备份。

SQL（LangChain SQLChatMessageHistory）是运行时主存储，
文件系统（FileHistoryStore）是离线备份，供压缩策略等场景读取。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import Engine

if TYPE_CHECKING:
    from langchain_core.chat_history import BaseChatMessageHistory
    from langchain_core.messages import BaseMessage

    from src.ai.core.memory.history_store import FileHistoryStore

logger = logging.getLogger(__name__)


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
