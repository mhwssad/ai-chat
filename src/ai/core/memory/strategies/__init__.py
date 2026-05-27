"""记忆策略工厂 — 创建 CompressionStrategy。"""

import logging

from src.ai.config.settings import settings
from src.ai.core.memory.history import ChatHistoryManager
from .base import BaseMemoryStrategy

logger = logging.getLogger(__name__)


def create_memory_strategy(
    history_manager: ChatHistoryManager,
    llm=None,
) -> BaseMemoryStrategy:
    """创建压缩策略实例。

    Args:
        history_manager: 对话历史管理器。
        llm: LangChain BaseChatModel，压缩策略必须。

    Returns:
        CompressionStrategy 实例。

    Raises:
        ValueError: LLM 为 None 时抛出。
    """
    if llm is None:
        raise ValueError("compression 策略需要 LLM 实例，请检查模型配置")

    from .compression import CompressionStrategy
    from src.ai.core.memory.history_store import FileHistoryStore
    from src.ai.config.base_config import project_root

    file_store = FileHistoryStore(project_root / settings.memory.memory_dir)
    return CompressionStrategy(
        history_manager,
        file_store,
        llm,
        max_messages=settings.memory.compression_max_messages,
        keep_recent=settings.memory.compression_keep_recent,
    )
