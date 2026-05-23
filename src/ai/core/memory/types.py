"""记忆模块类型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

MemoryType = Literal["user", "feedback", "project", "reference"]
MemoryScope = Literal["session", "user", "project", "team"]

MEMORY_TYPES: tuple[MemoryType, ...] = ("user", "feedback", "project", "reference")


@dataclass(frozen=True)
class MemoryHeader:
    """记忆 Markdown 文件头信息。"""

    path: str
    memory_type: MemoryType
    description: str
    modified_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RelevantMemory:
    """相关记忆结果。"""

    path: str
    memory_type: MemoryType
    description: str
    score: float
    content: str = ""


@dataclass(frozen=True)
class MemoryWriteRequest:
    """写入记忆请求。"""

    content: str
    memory_type: MemoryType = "project"
    scope: MemoryScope = "project"
    description: str = ""
    session_id: str | None = None
    source_type: str = "manual"
    source_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

