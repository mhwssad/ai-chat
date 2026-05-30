"""Markdown 标题切割器。"""

from pathlib import Path
from typing import Any

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from .base import SplitChunk, SplitterStrategy
from .registry import register_splitter

_DEFAULT_HEADERS: list[tuple[str, str]] = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]


@register_splitter(priority=100, name="markdown")
class MarkdownSplitter(SplitterStrategy):
    """基于 Markdown 标题层级的切割器。

    两阶段处理：
    1. 按标题层级（H1/H2/H3）切割，保留标题元数据。
    2. 对超出 chunk_size 的段落，用 RecursiveCharacterTextSplitter 二次切割。

    Args:
        chunk_size: 每个切片的最大字符数。
        chunk_overlap: 相邻切片的重叠字符数。
        headers_to_split_on: 标题层级配置。
    """

    def __init__(
        self,
        *,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        headers_to_split_on: list[tuple[str, str]] | None = None,
    ) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on or _DEFAULT_HEADERS,
            strip_headers=False,
        )

    def can_file_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in (".md", ".markdown")

    def can_text_handle(self, text: str, metadata: dict[str, Any]) -> bool:
        source = metadata.get("source", "")
        if source and Path(source).suffix.lower() in (".md", ".markdown"):
            return True
        return any(line.startswith("# ") for line in text.split("\n")[:10])

    def split_text(
        self, text: str, *, metadata: dict[str, Any] | None = None
    ) -> list[SplitChunk]:
        if not text.strip():
            return []
        md_docs = self._md_splitter.split_text(text)
        char_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
        )
        final_docs = char_splitter.split_documents(md_docs)
        return [
            SplitChunk(
                index=i,
                content=doc.page_content,
                strategy="markdown",
                metadata=doc.metadata,
            )
            for i, doc in enumerate(final_docs)
        ]
