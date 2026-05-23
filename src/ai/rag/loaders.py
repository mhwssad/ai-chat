"""RAG 文件加载。"""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path

from src.ai.exception.base_exception import BaseExceptions


class RagLoadError(BaseExceptions):
    """RAG 文件加载失败。"""


@dataclass(frozen=True)
class LoadedDocument:
    source_path: str
    content: str
    title: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None


TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".csv",
    ".sql",
    ".toml",
    ".ini",
    ".env",
}


class FileDocumentLoader:
    """读取本地文本类文件。"""

    def load(self, path: str | Path) -> LoadedDocument:
        file_path = Path(path)
        if not file_path.exists() or not file_path.is_file():
            raise RagLoadError("文件不存在", context={"path": str(file_path)})
        if file_path.suffix.lower() not in TEXT_EXTENSIONS:
            raise RagLoadError("暂不支持的文件类型", context={"path": str(file_path), "suffix": file_path.suffix})
        data = file_path.read_bytes()
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError:
            content = data.decode("gbk", errors="ignore")
        return LoadedDocument(
            source_path=str(file_path.resolve()),
            content=content,
            title=file_path.name,
            mime_type=mimetypes.guess_type(file_path.name)[0] or "text/plain",
            size_bytes=len(data),
        )

