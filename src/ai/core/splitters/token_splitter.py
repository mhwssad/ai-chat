"""Token 切割器。"""

from pathlib import Path
from typing import Any

from langchain_text_splitters import TokenTextSplitter

from .base import SplitChunk, SplitterStrategy


class TokenSplitter(SplitterStrategy):
    """基于 tiktoken 的 Token 精确切割器。

    使用 cl100k_base 编码器（GPT-4 同款）按 token 数切割文本。

    Args:
        chunk_size: 每个切片的最大 token 数。
        chunk_overlap: 相邻切片的重叠 token 数。
    """

    def __init__(self, *, chunk_size: int = 800, chunk_overlap: int = 120) -> None:
        self._splitter = TokenTextSplitter(
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
            SplitChunk(index=i, content=c, strategy="token")
            for i, c in enumerate(chunks)
        ]


# ── 自注册 ──────────────────────────────────────────────────────────────────
from .registry import splitter_registry  # noqa: E402

splitter_registry.register(TokenSplitter, priority=300, name="token")
