"""按固定字符数分割器 — 简单按字符数切割，不关心语义边界。"""

from ..factory import register_splitter
from ..models import TextSplitter


@register_splitter("character")
class CharacterSplitter(TextSplitter):
    """按固定字符数分割，可选分隔符。"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50, separator: str = "\n\n", **kwargs) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._separator = separator

    def split(self, documents: list[dict]) -> list[dict]:
        from langchain_text_splitters import CharacterTextSplitter

        splitter = CharacterTextSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            separator=self._separator,
        )
        chunks = []
        for doc in documents:
            texts = splitter.split_text(doc["content"])
            for text in texts:
                chunks.append({"content": text, "metadata": doc.get("metadata", {})})
        return chunks
