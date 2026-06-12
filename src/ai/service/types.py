"""共享服务层数据类型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatOptions:
    """对话选项 — 控制单次对话行为。"""

    session_id: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    max_rounds: int = 10
    tools: list[str] | None = None
    enable_memory: bool = True
    enable_tools: bool = True
    enable_rag: bool = False
    enable_agent: bool = False
    extract_memory: bool = True
    streaming: bool = False


@dataclass
class ChatResult:
    """对话执行结果。"""

    content: str = ""
    session_id: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    error: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    context_sources: list[dict[str, Any]] = field(default_factory=list)
