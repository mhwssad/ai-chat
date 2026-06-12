"""记忆向量存储 — 基于 Chroma 的记忆向量索引。"""

from __future__ import annotations

from src.ai.config.logging_setup import get_logger
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .types import MemoryEntry

logger = get_logger(__name__)


class MemoryVectorStore:
    """记忆向量存储。

    使用 Chroma 存储记忆的向量表示，支持语义相似度搜索。
    作为三层搜索架构的中间层，降低 LLM 精排的候选集规模。

    Args:
        persist_directory: Chroma 持久化目录。
        collection_name: collection 名称。
        embedding_fn: Embedding 函数（接受文本列表，返回向量列表）。
    """

    def __init__(
        self,
        *,
        persist_directory: str,
        collection_name: str = "memory_vectors",
        embedding_fn: Any = None,
    ) -> None:
        self._persist_dir = persist_directory
        self._collection_name = collection_name
        self._embedding_fn = embedding_fn
        self._client: Any = None
        self._collection: Any = None

    def _ensure_initialized(self) -> None:
        """惰性初始化 Chroma 客户端。"""
        if self._client is not None:
            return

        import chromadb

        self._client = chromadb.PersistentClient(path=self._persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.debug("记忆向量存储已初始化: %s", self._persist_dir)

    def index_entry(self, entry: MemoryEntry) -> None:
        """将单条记忆写入向量库。

        Args:
            entry: 记忆条目。
        """
        self._ensure_initialized()

        text = f"{entry.description}\n{entry.content}"
        doc_id = entry.name

        embedding = None
        if self._embedding_fn is not None:
            try:
                embedding = self._embedding_fn([text])[0]
            except Exception:
                logger.warning("生成记忆 embedding 失败: %s", doc_id, exc_info=True)

        metadata = {
            "memory_type": entry.memory_type,
            "name": entry.name,
            "description": entry.description[:200],
        }

        try:
            kwargs: dict[str, Any] = {
                "ids": [doc_id],
                "documents": [text],
                "metadatas": [metadata],
            }
            if embedding is not None:
                kwargs["embeddings"] = [embedding]
            self._collection.upsert(**kwargs)
        except Exception:
            logger.warning("写入记忆向量失败: %s", doc_id, exc_info=True)

    def search(self, query: str, top_k: int = 20) -> list[dict[str, Any]]:
        """向量相似度搜索。

        Args:
            query: 查询文本。
            top_k: 返回结果数量。

        Returns:
            搜索结果列表，每项包含 id, metadata, distance。
        """
        self._ensure_initialized()

        if self._collection.count() == 0:
            return []

        embedding = None
        if self._embedding_fn is not None:
            try:
                embedding = self._embedding_fn([query])[0]
            except Exception:
                logger.warning("生成查询 embedding 失败", exc_info=True)

        try:
            kwargs: dict[str, Any] = {
                "query_texts": [query] if embedding is None else None,
                "query_embeddings": [embedding] if embedding is not None else None,
                "n_results": min(top_k, self._collection.count()),
            }
            results = self._collection.query(**kwargs)
        except Exception:
            logger.warning("记忆向量搜索失败", exc_info=True)
            return []

        output: list[dict[str, Any]] = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                output.append(
                    {
                        "id": doc_id,
                        "metadata": results["metadatas"][0][i]
                        if results["metadatas"]
                        else {},
                        "document": results["documents"][0][i]
                        if results["documents"]
                        else "",
                        "distance": results["distances"][0][i]
                        if results["distances"]
                        else 1.0,
                    }
                )
        return output

    def rebuild(self, entries: list[MemoryEntry]) -> None:
        """全量重建向量索引。

        Args:
            entries: 所有记忆条目。
        """
        self._ensure_initialized()

        # 删除旧数据
        try:
            all_ids = self._collection.get()["ids"]
            if all_ids:
                self._collection.delete(ids=all_ids)
        except Exception:
            logger.warning("清空记忆向量索引失败", exc_info=True)

        # 批量写入
        for entry in entries:
            self.index_entry(entry)

        logger.info("记忆向量索引已重建: %d 条", len(entries))

    def delete_entry(self, name: str) -> None:
        """删除单条记忆的向量。

        Args:
            name: 记忆名称。
        """
        self._ensure_initialized()
        try:
            self._collection.delete(ids=[name])
        except Exception:
            logger.debug("删除记忆向量失败: %s", name, exc_info=True)

    def get_stats(self) -> dict[str, int]:
        """获取向量库统计。"""
        self._ensure_initialized()
        return {"total_entries": self._collection.count()}
