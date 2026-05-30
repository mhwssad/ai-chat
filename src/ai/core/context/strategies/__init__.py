"""记忆策略工厂 — 创建 CompressionStrategy。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from src.ai.core.memory.history import ChatHistoryManager
    from src.ai.core.memory.history_store import FileHistoryStore

    from .base import BaseMemoryStrategy

logger = logging.getLogger(__name__)


def create_memory_strategy(
    history_manager: ChatHistoryManager,
    file_store: FileHistoryStore,
    llm: BaseChatModel,
    prompt_service: object,
    *,
    max_messages: int = 30,
    keep_recent: int = 10,
    full_compact_threshold: int = 100,
) -> BaseMemoryStrategy:
    """创建压缩策略实例。

    Args:
        history_manager: 对话历史管理器。
        file_store: 文件历史存储。
        llm: LangChain BaseChatModel。
        prompt_service: 提示词服务。
        max_messages: 触发压缩的最大消息数。
        keep_recent: 保留的最近消息数。
        full_compact_threshold: 触发全量压缩的消息数阈值。

    Returns:
        CompressionStrategy 实例。
    """
    from .compression import CompressionStrategy

    return CompressionStrategy(
        history_manager,
        file_store,
        llm,
        prompt_service,
        max_messages=max_messages,
        keep_recent=keep_recent,
        full_compact_threshold=full_compact_threshold,
    )
