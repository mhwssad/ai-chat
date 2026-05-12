"""Memory 模块 — 会话管理、对话缓冲、长期摘要。"""

from src.ai_chat.memory.factory import memory_factory, register_memory
from src.ai_chat.memory.manager import ConversationMemory
from src.ai_chat.memory.models import (
    MemoryConfig,
    MemoryProvider,
    MemoryProviderNotFoundException,
    MessageRecord,
    Session,
    SessionNotFoundException,
    message_to_record,
    record_to_message,
)
from src.ai_chat.memory.menu import menu_memory

# 触发自动发现
from src.ai_chat.memory import providers as _providers

__all__ = [
    "memory_factory",
    "register_memory",
    "ConversationMemory",
    "MemoryConfig",
    "MemoryProvider",
    "MemoryProviderNotFoundException",
    "MessageRecord",
    "Session",
    "SessionNotFoundException",
    "message_to_record",
    "record_to_message",
    "menu_memory",
]
