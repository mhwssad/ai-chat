"""文本切割器模块。

采用职责链模式，各切割器自注册到 SplitterRegistry，ChainSplitter 按优先级遍历。

示例::

    from src.ai.core.rag.splitters import ChainSplitter
    from langchain_core.documents import Document

    splitter = ChainSplitter()

    # 切割纯文本
    chunks = splitter.split_text("Hello, World!")

    # 切割 Document
    doc = Document(page_content="...", metadata={"source": "file.md"})
    chunks = splitter.split_document(doc)

    # 注册自定义切割器
    from src.ai.core.container import container
    splitter_registry = container.rag_container.splitter_registry()
    splitter_registry.register(MySplitter, priority=150, name="my_splitter")
"""

from src.ai.exception.rag_exception import RagError as SplitterError
from .base import LangchainSplitterAdapter, SplitChunk, SplitterStrategy
from .chain_splitter import ChainSplitter
from .registry import SplitterRegistry

# 惰性导入：具体切割器类和 DI 容器单例
_LAZY_IMPORTS = {
    "MarkdownSplitter": ".markdown",
    "CodeSplitter": ".code",
    "TokenSplitter": ".token_splitter",
    "RecursiveSplitter": ".recursive",
    "EXTENSION_LANGUAGE": ".code",
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # 基类
    "SplitterStrategy",
    "SplitChunk",
    "LangchainSplitterAdapter",
    # 注册表
    "SplitterRegistry",
    # 编排器
    "ChainSplitter",
    # 切割器
    "RecursiveSplitter",
    "MarkdownSplitter",
    "CodeSplitter",
    "TokenSplitter",
    # 映射表
    "EXTENSION_LANGUAGE",
    # 异常
    "SplitterError",
]
