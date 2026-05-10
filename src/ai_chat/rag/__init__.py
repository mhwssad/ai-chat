"""RAG 模块 — 向量存储 + 文档处理 + 文本分割 + RAG 链。"""

from .factory import rag_factory, register_vectorstore, register_loader, register_splitter
from .chain import RAGChain
from .models import VectorStoreConfig, VectorStoreProvider, DocumentLoader, TextSplitter

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
