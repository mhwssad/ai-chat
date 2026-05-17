"""Memory 模块 — 会话管理、对话缓冲、长期摘要。

模块职责:
- 定义存储后端策略接口（MemoryProvider ABC）和数据模型（SQLModel 表 + Pydantic 传输模型）
- 提供两种存储实现：SQLite 持久化、内存临时存储
- ConversationMemory 高层编排器：token 感知的上下文压缩 + 长期摘要
- 通过 @register_memory 装饰器实现供应商自动注册

加载顺序（重要）:
1. factory.py — 注册装饰器和工厂单例
2. manager.py — ConversationMemory 编排器
3. models.py — 数据模型和 ABC
4. providers/ — 自动发现存储后端实现，触发装饰器注册
"""

from src.ai_chat.memory.factory import memory_factory, register_memory
from src.ai_chat.memory.manager import ConversationMemory, ContextInfo, ContextMessage, SessionDetail, SessionManager
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

# 触发自动发现，导入 providers 目录下所有模块以执行 @register_memory 装饰器
from src.ai_chat.memory import providers as _providers  # noqa: F401

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
    "ContextInfo",
    "ContextMessage",
    "SessionDetail",
    "SessionManager",
]
