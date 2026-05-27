"""纯文本读取加载器，支持多编码自动检测。"""

import mimetypes
from pathlib import Path

from langchain_core.documents import Document

from .base import LoaderStrategy


class PlainTextLoader(LoaderStrategy):
    """纯文本读取加载器。

    依次尝试多种编码读取文件，最终回退到 latin-1。

    Args:
        encodings: 尝试的编码列表，默认 ["utf-8", "gbk", "latin-1"]。
    """

    def __init__(self, encodings: list[str] | None = None) -> None:
        self._encodings = encodings or ["utf-8", "gbk", "latin-1"]

    def can_handle(self, file_path: Path) -> bool:
        """兜底策略，始终返回 True。"""
        return True

    def _load_single(self, file_path: Path) -> list[Document]:
        """以纯文本方式读取文件。"""
        content: str | None = None
        for enc in self._encodings:
            try:
                content = file_path.read_text(encoding=enc)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if content is None:
            content = file_path.read_bytes().decode("latin-1")

        mime_type = mimetypes.guess_type(file_path.name)[0]
        return [
            Document(
                page_content=content,
                metadata={
                    "source": str(file_path.resolve()),
                    "title": file_path.name,
                    "mime_type": mime_type,
                    "size_bytes": file_path.stat().st_size,
                    "file_label": "text",
                    "page_count": 1,
                    "fallback": True,
                },
            )
        ]


# ── 自注册 ──────────────────────────────────────────────────────────────────
from .registry import loader_registry  # noqa: E402

loader_registry.register(PlainTextLoader, priority=900, name="plain_text")
