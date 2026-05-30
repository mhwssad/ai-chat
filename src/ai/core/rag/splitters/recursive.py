"""递归字符切割器。"""

from pathlib import Path
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from .base import SplitChunk, SplitterStrategy
from .registry import register_splitter


@register_splitter(priority=900, name="recursive")
class RecursiveSplitter(SplitterStrategy):
    """基于 RecursiveCharacterTextSplitter 的通用切割器。

    使用分层分隔符（段落 → 换行 → 句子 → 词）递归切割文本。
    作为兜底策略，始终返回 can_handle=True。

    Args:
        chunk_size: 每个切片的最大字符数。
        chunk_overlap: 相邻切片的重叠字符数。
    """

    def __init__(self, *, chunk_size: int = 800, chunk_overlap: int = 120) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def can_file_handle(self, file_path: Path) -> bool:
        return True

    def can_text_handle(self, text: str, metadata: dict[str, Any]) -> bool:
        return True

    def split_text(
        self, text: str, *, metadata: dict[str, Any] | None = None
    ) -> list[SplitChunk]:
        if not text.strip():
            return []
        chunks = self._splitter.split_text(text)
        return [
            SplitChunk(index=i, content=c, strategy="recursive")
            for i, c in enumerate(chunks)
        ]
