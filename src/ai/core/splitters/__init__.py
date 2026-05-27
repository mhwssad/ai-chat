"""文本切割器模块。

采用职责链模式，各切割器自注册到 SplitterRegistry，ChainSplitter 按优先级遍历。

示例::

    from src.ai.core.splitters import ChainSplitter
    from langchain_core.documents import Document

    splitter = ChainSplitter()

    # 切割纯文本
    chunks = splitter.split_text("Hello, World!")

    # 切割 Document
    doc = Document(page_content="...", metadata={"source": "file.md"})
    chunks = splitter.split_document(doc)

    # 注册自定义切割器
    from src.ai.core.splitters import splitter_registry
    splitter_registry.register(MySplitter, priority=150, name="my_splitter")
"""

from src.ai.exception.rag_exception import RagError as SplitterError
from .base import LangchainSplitterAdapter, SplitChunk, SplitterStrategy
from .chain_splitter import ChainSplitter
from .registry import SplitterRegistry, splitter_registry

# 导入各切割器模块以触发自注册
from .markdown import MarkdownSplitter  
from .code import CodeSplitter, EXTENSION_LANGUAGE  
from .token_splitter import TokenSplitter   
from .recursive import RecursiveSplitter  

__all__ = [
    # 基类
    "SplitterStrategy",
    "SplitChunk",
    "LangchainSplitterAdapter",
    # 注册表
    "SplitterRegistry",
    "splitter_registry",
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
