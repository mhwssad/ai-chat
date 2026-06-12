"""RAG 知识库能力 — 基于 langchain-chroma，支持会话隔离。

子模块延迟导入，避免 import 时触发 langchain_core 冷启动。
"""

from __future__ import annotations

from typing import Any

from src.ai.exception.rag_exception import RagEmbeddingError, RagError
from src.ai.core.rag.types import RAGSearchConfig, RAGSearchResult


# ── 惰性导入 ─────────────────────────────────────────────────────

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "HashEmbeddings": ("src.ai.core.rag.embeddings", "HashEmbeddings"),
    "RagDocumentInfo": ("src.ai.core.rag.service", "RagDocumentInfo"),
    "RagSearchResult": ("src.ai.core.rag.service", "RagSearchResult"),
    "RagService": ("src.ai.core.rag.service", "RagService"),
    "create_rag_service": ("src.ai.core.rag.service", "create_rag_service"),
    "RAGQueryEncoder": ("src.ai.core.rag.encoder", "RAGQueryEncoder"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        mod = importlib.import_module(module_path)
        return getattr(mod, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "HashEmbeddings",
    "RagDocumentInfo",
    "RagEmbeddingError",
    "RagError",
    "RagSearchResult",
    "RagService",
    "RAGQueryEncoder",
    "RAGSearchConfig",
    "RAGSearchResult",
    "create_rag_service",
]
