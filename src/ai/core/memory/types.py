"""记忆模块类型定义。

包含长期记忆类型（MemoryEntry 等）。
统一使用 4 个分类：user、feedback、project、reference。
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal


# ── 记忆分类（参考 Claude Code） ──────────────────────────────

MemoryType = Literal["user", "feedback", "project", "reference"]
MEMORY_TYPES: tuple[MemoryType, ...] = ("user", "feedback", "project", "reference")
MemoryScope = Literal["session", "user", "project", "team"]
MemorySourceType = Literal["message", "tool_result", "manual", "auto_memory", "team_memory"]
MemoryStatus = Literal["active", "deleted", "disabled"]

_SLUG_RE = re.compile(r"[^a-zA-Z0-9一-鿿]+")


def generate_memory_name(
    memory_type: MemoryType, text: str, *, with_hash: bool = False
) -> str:
    """根据记忆类型和内容生成文件名安全的名称。

    Args:
        memory_type: 记忆分类。
        text: 记忆内容文本。
        with_hash: 是否附加内容哈希后缀（避免同 slug 碰撞）。

    Returns:
        格式为 ``{memory_type}-{slug}`` 或 ``{memory_type}-{slug}-{hash}`` 的名称。
    """
    slug = _SLUG_RE.sub("-", text[:30]).strip("-")[:30]
    if with_hash:
        hash_part = sha256(text.encode("utf-8")).hexdigest()[:8]
        return f"{memory_type}-{slug}-{hash_part}"
    return f"{memory_type}-{slug}"


@dataclass(frozen=True)
class MemoryEntry:
    """记忆条目（从文件解析或内存构造）。"""

    name: str
    memory_type: MemoryType
    description: str
    content: str
    file_path: Path | None = None
    session_id: str | None = None
    scope: MemoryScope = "project"
    source_type: MemorySourceType = "manual"
    source_id: str | None = None
    status: MemoryStatus = "active"
    created_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MemorySearchResult:
    """搜索结果。"""

    entry: MemoryEntry
    score: float
    match_type: str  # "exact" | "partial" | "keyword" | "vector" | "llm_relevance"


@dataclass
class MemoryWriteRequest:
    """写入记忆请求。"""

    content: str
    memory_type: MemoryType = "project"
    name: str | None = None
    description: str | None = None
    scope: MemoryScope = "project"
    source_type: MemorySourceType = "manual"
    source_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompressedSummary:
    """压缩摘要数据。"""

    summary: str
    compressed_range: tuple[int, int]
    file_references: list[dict[str, Any]] = field(default_factory=list)
    updated_at: datetime | None = None
