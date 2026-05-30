"""记忆策略基类 — 定义策略接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage

    from src.ai.core.memory.history import ChatHistoryManager


class BaseMemoryStrategy(ABC):
    """记忆策略基类。

    所有策略共享 ChatHistoryManager（SQLChatMessageHistory）作为持久化后端，
    但在上下文构建时采用不同的压缩/检索方式。
    """

    def __init__(self, history_manager: ChatHistoryManager) -> None:
        self._history = history_manager

    @abstractmethod
    def build_context_messages(
        self,
        session_id: str | None,
        system_prompt: str,
        *,
        max_tokens: int | None = None,
    ) -> list[BaseMessage]:
        """构建用于发送给 LLM 的上下文消息列表（同步）。"""

    @abstractmethod
    def add_message(self, session_id: str, message: BaseMessage) -> None:
        """添加消息到历史记录（同步）。"""

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """策略名称标识。"""

    async def abuild_context_messages(
        self,
        session_id: str | None,
        system_prompt: str,
        *,
        max_tokens: int | None = None,
    ) -> list[BaseMessage]:
        """构建上下文消息列表（异步，默认委托给同步版本）。"""
        return self.build_context_messages(
            session_id, system_prompt, max_tokens=max_tokens
        )

    async def aadd_message(self, session_id: str, message: BaseMessage) -> None:
        """添加消息到历史记录（异步，默认委托给同步版本）。"""
        return self.add_message(session_id, message)
