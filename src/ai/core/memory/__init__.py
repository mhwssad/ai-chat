"""统一记忆与上下文管理模块。

集成长期记忆（文件系统）、对话历史（LangChain SQLChatMessageHistory）
和上下文构建（策略驱动）。

所有子模块延迟导入，避免 import 时触发 langchain_core 冷启动。
"""

from __future__ import annotations

from typing import Any

# 轻量级类型和工具（不依赖 langchain）
from src.ai.core.memory.types import (
    MEMORY_TYPES,
    CompressedSummary,
    MemoryEntry,
    MemorySearchResult,
    MemoryType,
    MemoryWriteRequest,
    generate_memory_name,
)

# 记忆异常
from src.ai.exception.memory_exception import (
    MemoryException,
    MemoryPathError,
    MemoryScanError,
)

# 路径工具（纯文件操作，无 langchain 依赖）
from src.ai.core.memory.paths import (
    MemoryPathResolver,
    sanitize_path_name,
    validate_memory_path,
)


# ── 惰性导入 ─────────────────────────────────────────────────────

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # (module_path, attribute_name)
    "MemoryExtractor": ("src.ai.core.memory.extractor", "MemoryExtractor"),
    "MemorySearcher": ("src.ai.core.memory.searcher", "MemorySearcher"),
    "MemoryPromptBuilder": ("src.ai.core.memory.prompt", "MemoryPromptBuilder"),
    "MemoryStore": ("src.ai.core.memory.store", "MemoryStore"),
    "MemoryIndex": ("src.ai.core.memory.store", "MemoryIndex"),
    "FileHistoryStore": ("src.ai.core.memory.history_store", "FileHistoryStore"),
    "FileMessageStore": ("src.ai.core.memory.history_store", "FileMessageStore"),
    "FileSummaryStore": ("src.ai.core.memory.history_store", "FileSummaryStore"),
    "MemoryService": ("src.ai.core.memory.service", "MemoryService"),
    "ChatHistoryManager": ("src.ai.core.memory.history", "ChatHistoryManager"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        import importlib

        mod = importlib.import_module(module_path)
        return getattr(mod, attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # 类型与工具
    "MEMORY_TYPES",
    "CompressedSummary",
    "MemoryEntry",
    "MemorySearchResult",
    "MemoryType",
    "MemoryWriteRequest",
    "generate_memory_name",
    # 路径
    "MemoryPathResolver",
    "sanitize_path_name",
    "validate_memory_path",
    # 异常
    "MemoryException",
    "MemoryPathError",
    "MemoryScanError",
    # 惰性导入
    "MemoryExtractor",
    "MemorySearcher",
    "MemoryPromptBuilder",
    "MemoryStore",
    "MemoryIndex",
    "FileHistoryStore",
    "FileMessageStore",
    "FileSummaryStore",
    "MemoryService",
    "ChatHistoryManager",
]
