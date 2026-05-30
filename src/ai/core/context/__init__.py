"""上下文管理模块 — 收集、组装、压缩、缓存。

子模块延迟导入，避免 import 时触发 langchain_core 冷启动。
"""

from __future__ import annotations

from typing import Any

# 轻量级类型导入（纯 dataclass，无 langchain 依赖）
from src.ai.core.context.types import (
    ContextBuildRequest,
    ContextBuildResult,
    ContextCollectorResult,
    ContextSection,
    ContextSourceBudget,
    ContextSourcePriority,
)


# ── 惰性导入 ─────────────────────────────────────────────────────

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "ContextAssembler": ("src.ai.core.context.assembler", "ContextAssembler"),
    "estimate_tokens": ("src.ai.core.context.assembler", "estimate_tokens"),
    "ContextCollector": ("src.ai.core.context.collector", "ContextCollector"),
    "ContextCoordinator": ("src.ai.core.context.collector", "ContextCoordinator"),
    "FullCompact": ("src.ai.core.context.compact", "FullCompact"),
    "MicroCompact": ("src.ai.core.context.compact", "MicroCompact"),
    "extract_message_content": ("src.ai.core.context.compact", "extract_message_content"),
    "format_messages_to_text": ("src.ai.core.context.compact", "format_messages_to_text"),
    "validate_summary_sections": ("src.ai.core.context.compact", "validate_summary_sections"),
    "SystemPromptSections": ("src.ai.core.context.sections", "SystemPromptSections"),
    "ContextService": ("src.ai.core.context.service", "ContextService"),
    "BaseMemoryStrategy": ("src.ai.core.context.strategies.base", "BaseMemoryStrategy"),
    "CompressionStrategy": ("src.ai.core.context.strategies.compression", "CompressionStrategy"),
    "CompressionContextBuilder": ("src.ai.core.context.strategies.compression", "CompressionContextBuilder"),
    "create_memory_strategy": ("src.ai.core.context.strategies", "create_memory_strategy"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        mod = importlib.import_module(module_path)
        return getattr(mod, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ContextAssembler",
    "ContextBuildRequest",
    "ContextBuildResult",
    "ContextCollector",
    "ContextCollectorResult",
    "ContextCoordinator",
    "ContextSection",
    "ContextService",
    "ContextSourceBudget",
    "ContextSourcePriority",
    "FullCompact",
    "MicroCompact",
    "extract_message_content",
    "format_messages_to_text",
    "validate_summary_sections",
    "SystemPromptSections",
    "BaseMemoryStrategy",
    "CompressionStrategy",
    "CompressionContextBuilder",
    "create_memory_strategy",
    "estimate_tokens",
]
