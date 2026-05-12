"""Graphs 模块 — Agent 工厂 + 管理入口。"""

from .chat_agent import ChatAgent
from .chat_graph import ChatGraph
from .memory_agent import MemoryAgent
from .unified_agent import UnifiedAgent
from .factory import agent_factory
from .menu import menu_chat

# 注册所有 agent
agent_factory.register("unified", UnifiedAgent, supports_overrides=True, has_chat=True)
agent_factory.register("chat", ChatAgent, supports_overrides=True, has_chat=False)
agent_factory.register("memory", MemoryAgent, supports_overrides=False, has_chat=True)
agent_factory.register("chat_graph", ChatGraph, supports_overrides=False, has_chat=False)

__all__ = [
    "ChatAgent",
    "ChatGraph",
    "MemoryAgent",
    "UnifiedAgent",
    "agent_factory",
    "menu_chat",
]
