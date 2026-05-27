"""RAG 知识库能力 — 基于 langchain-chroma，支持会话隔离。"""

from src.ai.core.rag.embeddings import HashEmbeddings
from src.ai.exception.rag_exception import RagEmbeddingError, RagError
from src.ai.core.rag.service import (
    RagDocumentInfo,
    RagSearchResult,
    RagService,
    create_rag_service,
    rag_service,
)
from src.ai.core.rag.splitters import RagTextSplitter, TextChunk

__all__ = [
    "HashEmbeddings",
    "RagDocumentInfo",
    "RagEmbeddingError",
    "RagError",
    "RagSearchResult",
    "RagService",
    "RagTextSplitter",
    "TextChunk",
    "create_rag_service",
    "rag_service",
]
