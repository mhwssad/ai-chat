"""RAG 文本切分。"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str


class RagTextSplitter:
    """基于 LangChain 的递归文本切分器。"""

    def __init__(self, *, chunk_size: int = 800, chunk_overlap: int = 120) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def split(self, text: str) -> list[TextChunk]:
        chunks = self._splitter.split_text(text)
        return [TextChunk(index=index, content=chunk) for index, chunk in enumerate(chunks)]

