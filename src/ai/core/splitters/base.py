"""文本切割器基类和接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import TextSplitter


@dataclass(frozen=True)
class SplitChunk:
    """文本切割结果。

    Attributes:
        index: 切片序号（从 0 开始）。
        content: 切片文本内容。
        strategy: 使用的切割策略名称。
        metadata: 策略相关元数据（标题层级、语言名等）。
    """

    index: int
    content: str
    strategy: str
    metadata: dict[str, Any] = field(default_factory=dict)


class SplitterStrategy(ABC):
    """文本切割器策略基类。

    所有切割器继承此类，实现 can_file_handle()、can_text_handle() 和 split_text()。
    ChainSplitter 遍历注册表，用 can_*_handle() 过滤，首个成功的策略胜出。
    """

    @abstractmethod
    def can_file_handle(self, file_path: Path) -> bool:
        """根据文件路径判断能否处理。

        Args:
            file_path: 文件路径。

        Returns:
            True 表示可以处理。
        """

    @abstractmethod
    def can_text_handle(self, text: str, metadata: dict[str, Any]) -> bool:
        """根据文本内容和元数据判断能否处理。

        Args:
            text: 文本内容。
            metadata: 文档元数据。

        Returns:
            True 表示可以处理。
        """

    @abstractmethod
    def split_text(
        self, text: str, *, metadata: dict[str, Any] | None = None
    ) -> list[SplitChunk]:
        """切割纯文本。

        Args:
            text: 待切割的文本内容。
            metadata: 可选的文档元数据。

        Returns:
            切割结果列表。空文本返回空列表。
        """

    def split_document(self, doc: Document) -> list[SplitChunk]:
        """切割 langchain Document。

        Args:
            doc: langchain Document 对象。

        Returns:
            切割结果列表。
        """
        return self.split_text(doc.page_content, metadata=doc.metadata)


class LangchainSplitterAdapter(TextSplitter):
    """将 SplitterStrategy 适配为 langchain TextSplitter。

    继承 langchain_text_splitters.TextSplitter，可直接传入 langchain 管道。
    实际切割逻辑委托给内部的 SplitterStrategy。

    Args:
        strategy: SplitterStrategy 实例。
    """

    def __init__(self, strategy: SplitterStrategy) -> None:
        # chunk_size/chunk_overlap 由 strategy 内部管理，传默认值即可
        super().__init__(chunk_size=4000, chunk_overlap=200)
        self._strategy = strategy

    def split_text(self, text: str) -> list[str]:
        """切割文本，返回字符串列表（langchain 接口）。"""
        chunks = self._strategy.split_text(text)
        return [c.content for c in chunks]

    def split_documents(self, documents: Iterable[Document]) -> list[Document]:
        """切割 Document 列表，返回切割后的 Document 列表。"""
        results: list[Document] = []
        for doc in documents:
            chunks = self._strategy.split_document(doc)
            for chunk in chunks:
                metadata = {**doc.metadata, **chunk.metadata, "chunk_index": chunk.index}
                results.append(Document(page_content=chunk.content, metadata=metadata))
        return results
