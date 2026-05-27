"""对话历史管理 — 基于 LangChain SQLChatMessageHistory。"""

import logging
from typing import TYPE_CHECKING

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage
from langchain_community.chat_message_histories import SQLChatMessageHistory

from src.ai.config.settings import settings
from src.ai.storage.database import get_engine

if TYPE_CHECKING:
    from src.ai.core.memory.history_store import FileHistoryStore

logger = logging.getLogger(__name__)


class ChatHistoryManager:
    """对话历史管理器。

    基于 LangChain SQLChatMessageHistory，
    使用项目 SQLite 数据库存储对话消息。
    可选集成文件系统持久化。
    """

    def __init__(self, file_store: "FileHistoryStore | None" = None) -> None:
        self._engine = get_engine()
        self._table_name = settings.memory.history_table_name
        self._file_store = file_store

    def get_history(self, session_id: str) -> BaseChatMessageHistory:
        """获取指定会话的消息历史。"""
        return SQLChatMessageHistory(
            session_id=session_id,
            connection=self._engine,
            table_name=self._table_name,
        )

    def add_message(self, session_id: str, message: BaseMessage) -> None:
        """添加一条消息到历史（SQL + 可选文件）。"""
        history = self.get_history(session_id)
        history.add_message(message)
        if self._file_store and settings.memory.history_file_enabled:
            self._file_store.append_message(session_id, message)

    def get_messages(self, session_id: str) -> list[BaseMessage]:
        """获取会话的所有消息。"""
        history = self.get_history(session_id)
        return history.messages

    def clear_history(self, session_id: str) -> None:
        """清空会话历史。"""
        history = self.get_history(session_id)
        history.clear()

    def message_count(self, session_id: str) -> int:
        """获取会话消息数量。"""
        return len(self.get_messages(session_id))


# 模块级单例（延迟初始化）
_chat_history_manager: ChatHistoryManager | None = None


def get_chat_history_manager(
    file_store: "FileHistoryStore | None" = None,
) -> ChatHistoryManager:
    """获取对话历史管理器单例。"""
    global _chat_history_manager
    if _chat_history_manager is None:
        _chat_history_manager = ChatHistoryManager(file_store=file_store)
    return _chat_history_manager
