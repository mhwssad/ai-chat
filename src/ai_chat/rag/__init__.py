"""RAG 模块 — 向量存储 + 文档处理 + 文本分割。"""

from .factory import rag_factory, register_vectorstore, register_loader, register_splitter
from .models import VectorStoreConfig, VectorStoreProvider, DocumentLoader, TextSplitter

# RAGChain 已迁移到 chains 模块，此处保持向后兼容的 re-export
from src.ai_chat.chains.rag_chain import RAGChain

# 触发自动发现
from . import stores as _stores
from . import loaders as _loaders
from . import splitters as _splitters

__all__ = [
    "rag_factory",
    "register_vectorstore",
    "register_loader",
    "register_splitter",
    "RAGChain",
    "VectorStoreConfig",
    "VectorStoreProvider",
    "DocumentLoader",
    "TextSplitter",
]
