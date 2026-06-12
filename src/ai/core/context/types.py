"""上下文管理模块类型定义。

包含上下文构建请求/结果、收集器接口类型、段管理类型。
从 memory/types.py 迁移上下文相关类型，新增收集器和段管理类型。
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


# ── 上下文来源优先级 ─────────────────────────────────────────


class ContextSourcePriority(IntEnum):
    """上下文来源优先级（数值越小，优先级越高，越不容易被裁剪）。"""

    SYSTEM_PROMPT = 0
    CONVERSATION = 1
    MEMORY = 2
    TOOLS = 3
    RAG = 4


# ── 上下文段 ─────────────────────────────────────────────────


@dataclass(frozen=True)
class ContextSection:
    """系统提示的一个段。

    Attributes:
        name: 段名称（用于缓存键和日志）。
        content: 段内容文本。
        priority: 优先级，数值越小越靠前，越不容易被裁剪。
        cacheable: 是否可缓存（True = 会话内缓存，False = 每次重算）。
    """

    name: str
    content: str
    priority: int
    cacheable: bool = True


@dataclass(frozen=True)
class ContextCollectorResult:
    """单个收集器的结果。

    Attributes:
        sections: 收集到的上下文段列表。
        token_count: 估算的 token 总数。
    """

    sections: list[ContextSection] = field(default_factory=list)
    token_count: int = 0


# ── 上下文构建请求/结果 ──────────────────────────────────────


@dataclass
class ContextSourceBudget:
    """单个上下文来源的预算分配结果。"""

    source: str
    allocated_tokens: int = 0
    actual_tokens: int = 0
    truncated: bool = False


@dataclass
class ContextSourceSummary:
    """上下文来源摘要，用于 API 可解释展示。"""

    source: str
    item_count: int = 0
    token_count: int = 0
    truncated: bool = False
    cacheable: bool = False
    summary: str = ""


@dataclass
class ContextBuildRequest:
    """上下文构建请求。"""

    messages: list[Any] = field(default_factory=list)  # list[ChatMessage]
    model_config: Any = None  # ChatModelConfig
    session_id: str | None = None
    enable_memory: bool = True
    enable_tools: bool = False
    enable_rag: bool = False
    enable_agent: bool = False
    rag_content: str = ""
    custom_system_prompt: str | None = None
    memory_search_limit: int = 5
    safety_margin: int = 200
    rag_query: str = ""
    rag_top_k: int = 5


@dataclass
class ContextBuildResult:
    """上下文构建结果。"""

    messages: list[Any] = field(default_factory=list)  # list[BaseMessage | ChatMessage]
    system_message: str = ""
    sections: list[ContextSection] = field(default_factory=list)
    budget_report: list[ContextSourceBudget] = field(default_factory=list)
    source_summary: list[ContextSourceSummary] = field(default_factory=list)
    total_input_tokens: int = 0
    budget_enabled: bool = False
    strategy_used: str = ""
    restored_context: Any = None  # RestoredContext 实例（避免循环导入用 Any）
