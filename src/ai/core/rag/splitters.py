"""RAG 文本切分 — 委托给 core/splitters。"""

from dataclasses import dataclass

from langchain_core.documents import Document

from src.ai.config.settings import settings
from src.ai.core.splitters import ChainSplitter, SplitChunk


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str


class RagTextSplitter:
    """基于 core/splitters 的 RAG 文本切分器。

    内部使用 ChainSplitter 根据文件类型自动选择最佳切割策略。
    保持与原接口兼容的 split(text) -> list[TextChunk] 方法。
    新增 split_document(doc) -> list[SplitChunk] 方法支持富元数据。

    Args:
        chunk_size: 每个切片的最大字符数。
        chunk_overlap: 相邻切片的重叠字符数。
    """

    def __init__(
        self,
        *,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        rag = settings.rag
        self._inner = ChainSplitter(
            chunk_size=chunk_size if chunk_size is not None else rag.rag_chunk_size,
            chunk_overlap=chunk_overlap if chunk_overlap is not None else rag.rag_chunk_overlap,
        )

    def split(self, text: str) -> list[TextChunk]:
        """切割纯文本，返回兼容 TextChunk 列表。"""
        chunks = self._inner.split_text(text)
        return [TextChunk(index=c.index, content=c.content) for c in chunks]

    def split_document(self, doc: Document) -> list[SplitChunk]:
        """切割 Document，返回带元数据的 SplitChunk。"""
        return self._inner.split_document(doc)
