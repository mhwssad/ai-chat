"""RAG 索引元数据存储 — 基于文件 hash 的增量索引支持。"""

from __future__ import annotations

import hashlib
import json
from src.ai.config.logging_setup import get_logger
from dataclasses import asdict, dataclass
from pathlib import Path

logger = get_logger(__name__)


@dataclass
class IndexedFileMeta:
    """已索引文件的元数据。"""

    source_path: str
    content_hash: str
    chunk_ids: list[str]
    chunk_count: int
    indexed_at: str  # ISO 格式时间戳
    file_size: int
    mtime: float


class IndexMetaStore:
    """索引元数据持久化存储。

    使用 JSON 文件记录已索引文件的元数据，
    支持基于 content_hash 的增量更新判断。

    Args:
        persist_path: 元数据 JSON 文件路径。
    """

    def __init__(self, persist_path: str | Path) -> None:
        self._path = Path(persist_path)
        self._cache: dict[str, IndexedFileMeta] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """确保缓存已从文件加载。"""
        if self._loaded:
            return
        self._loaded = True
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for key, meta_dict in data.items():
                self._cache[key] = IndexedFileMeta(**meta_dict)
        except Exception:
            logger.warning("加载索引元数据失败: %s", self._path, exc_info=True)

    def _save(self) -> None:
        """持久化到文件。"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {key: asdict(meta) for key, meta in self._cache.items()}
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get(self, source_path: str) -> IndexedFileMeta | None:
        """获取文件的索引元数据。

        Args:
            source_path: 源文件路径。

        Returns:
            元数据，不存在返回 None。
        """
        self._ensure_loaded()
        return self._cache.get(source_path)

    def put(self, meta: IndexedFileMeta) -> None:
        """保存或更新文件的索引元数据。

        Args:
            meta: 元数据。
        """
        self._ensure_loaded()
        self._cache[meta.source_path] = meta
        self._save()

    def delete(self, source_path: str) -> bool:
        """删除文件的索引元数据。

        Args:
            source_path: 源文件路径。

        Returns:
            True 表示成功删除。
        """
        self._ensure_loaded()
        if source_path in self._cache:
            del self._cache[source_path]
            self._save()
            return True
        return False

    def list_all(self) -> list[IndexedFileMeta]:
        """列出所有索引元数据。"""
        self._ensure_loaded()
        return list(self._cache.values())


def compute_content_hash(text: str) -> str:
    """计算文本内容的 SHA-256 哈希。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_file_hash(path: Path) -> str:
    """计算文件内容的 SHA-256 哈希。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
