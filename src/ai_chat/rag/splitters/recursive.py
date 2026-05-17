"""递归字符分割器 — 按字符数递归分割，优先在段落/句子边界切分。"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..factory import register_splitter
from ..models import TextSplitter


@register_splitter("recursive", default=True)
class RecursiveCharacterSplitter(TextSplitter):
    """递归字符分割器，优先在段落、换行、句号等边界切分。"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50, **kwargs) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def split(self, documents: list[dict]) -> list[dict]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
        )
        chunks = []
        for doc in documents:
            texts = splitter.split_text(doc["content"])
            for text in texts:
                chunks.append({"content": text, "metadata": doc.get("metadata", {})})
        return chunks
