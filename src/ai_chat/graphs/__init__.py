"""Graphs 模块 — Agent 工厂 + 管理入口。"""

from .base import (
    GraphConfig,
    GraphError,
    GraphExecutionError,
    GraphRoutingError,
    PromptContext,
    _BaseAgent,
    extract_last_human_message,
    get_default_model,
    merge_context,
)
from .chat_agent import ChatAgent
from .chat_graph import ChatGraph
from .memory_agent import MemoryAgent
from .unified_agent import UnifiedAgent
from .observability import (
    GraphMetrics,
    GraphMetricsCollector,
    GraphMetricsSummary,
    graph_metrics_collector,
)
from .factory import agent_factory, register_graph
from .menu import menu_chat

# 注册所有 agent
agent_factory.register("unified", UnifiedAgent, supports_overrides=True, has_chat=True)
agent_factory.register("chat", ChatAgent, supports_overrides=True, has_chat=False)
agent_factory.register("memory", MemoryAgent, supports_overrides=False, has_chat=True)
agent_factory.register("chat_graph", ChatGraph, supports_overrides=False, has_chat=False)

__all__ = [
    # 基类与配置
    "GraphConfig",
    "GraphError",
    "GraphExecutionError",
    "GraphRoutingError",
    "PromptContext",
    "_BaseAgent",
    "merge_context",
    "extract_last_human_message",
    "get_default_model",
    # Agent
    "ChatAgent",
    "ChatGraph",
    "MemoryAgent",
    "UnifiedAgent",
    # 可观测性
    "GraphMetrics",
    "GraphMetricsCollector",
    "GraphMetricsSummary",
    "graph_metrics_collector",
    # 工厂
    "agent_factory",
    "register_graph",
    # 菜单
    "menu_chat",
]
