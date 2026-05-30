"""纯文本读取加载器，支持多编码自动检测。"""

import mimetypes
from pathlib import Path

from langchain_core.documents import Document

from src.ai.config.loader_settings import PlainTextSettings
from .base import LoaderStrategy


class PlainTextLoader(LoaderStrategy):
    """纯文本读取加载器。

    依次尝试多种编码读取文件，最终回退到 latin-1。
    编码列表通过 PlainTextSettings 配置驱动。

    Args:
        settings: 纯文本加载器配置。
    """

    priority = 900
    name = "plain_text"

    def __init__(self, settings: PlainTextSettings) -> None:
        self._settings = settings

    def can_handle(self, file_path: Path) -> bool:
        """兜底策略，始终返回 True。"""
        return True

    def _load_single(self, file_path: Path) -> list[Document]:
        """以纯文本方式读取文件。"""
        content: str | None = None
        for enc in self._settings.encodings:
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
