"""记忆模块类型定义。

包含长期记忆类型（MemoryEntry 等）和上下文构建类型（ContextBuildRequest 等）。
统一使用 4 个分类：user、feedback、project、reference。
"""

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Literal


# ── 记忆分类（参考 Claude Code） ──────────────────────────────

MemoryType = Literal["user", "feedback", "project", "reference"]
MEMORY_TYPES: tuple[MemoryType, ...] = ("user", "feedback", "project", "reference")


@dataclass(frozen=True)
class MemoryEntry:
    """记忆条目（从文件解析或内存构造）。"""

    name: str
    memory_type: MemoryType
    description: str
    content: str
    file_path: Path | None = None
    session_id: str | None = None
    created_at: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MemorySearchResult:
    """搜索结果。"""

    entry: MemoryEntry
    score: float
    match_type: str  # "exact" | "partial" | "keyword" | "vector"


@dataclass
class MemoryWriteRequest:
    """写入记忆请求。"""

    content: str
    memory_type: MemoryType = "project"
    name: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ── 记忆策略类型 ─────────────────────────────────────────────


class MemoryStrategyType(str, Enum):
    """记忆策略类型。

    通过 settings.memory.memory_strategy 配置选择：
    - buffer: 保留所有消息，超限时裁剪
    - summary: 长对话自动摘要压缩
    - summary_buffer: 摘要 + 近期缓冲混合
    - vector: 基于 ChromaDB 的语义搜索
    """

    BUFFER = "buffer"
    SUMMARY = "summary"
    SUMMARY_BUFFER = "summary_buffer"
    VECTOR = "vector"
    COMPRESSION = "compression"


@dataclass(frozen=True)
class CompressedSummary:
    """压缩摘要数据。"""

    summary: str
    compressed_range: tuple[int, int]
    file_references: list[dict[str, Any]] = field(default_factory=list)
    updated_at: Any | None = None


@dataclass(frozen=True)
class RAGSearchConfig:
    """RAG 检索配置。"""

    enabled: bool = True
    top_k: int = 5
    optimize_query: bool = True
    merge_strategy: str = "deduplicate"


# ── 上下文构建类型（原 context/types.py） ──────────────────────


class ContextSourcePriority(IntEnum):
    """上下文来源优先级（数值越小，优先级越高）。"""

    SYSTEM_PROMPT = 0
    CONVERSATION = 1
    MEMORY = 2
    TOOLS = 3
    RAG = 4


@dataclass(frozen=True)
class ContextSourceBudget:
    """单个上下文来源的预算分配结果。"""

    source: str
    allocated_tokens: int
    actual_tokens: int = 0
    truncated: bool = False


@dataclass
class ContextBuildRequest:
    """上下文构建请求。"""

    messages: list[Any] = field(default_factory=list)  # list[ChatMessage]
    model_config: Any = None  # ChatModelConfig
    session_id: str | None = None
    enable_memory: bool = True
    enable_tools: bool = False
    rag_content: str = ""
    custom_system_prompt: str | None = None
    memory_search_limit: int = 5
    safety_margin: int = 200
    enable_rag: bool = False
    rag_query: str = ""
    rag_top_k: int = 5


@dataclass
class ContextBuildResult:
    """上下文构建结果。"""

    messages: list[Any] = field(default_factory=list)  # list[BaseMessage | ChatMessage]
    system_message: str = ""
    budget_report: list[ContextSourceBudget] = field(default_factory=list)
    total_input_tokens: int = 0
    budget_enabled: bool = False
    strategy_used: str = ""
