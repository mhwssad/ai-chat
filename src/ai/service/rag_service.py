"""RAG API 服务 — RagService 的薄包装，提供异步方法。

共享服务层，CLI 和 API 路由统一使用。
"""

from __future__ import annotations

from src.ai.config.logging_setup import get_logger
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.ai.utils.thread_pool import ThreadPoolManager

logger = get_logger(__name__)


class RagApiService:
    """RAG API 服务。

    职责：
    1. 文档索引（文件、URL、文本、目录）
    2. 向量搜索和混合搜索
    3. 文档管理（列表、删除、统计）
    """

    def __init__(
        self,
        *,
        rag_service: Any,
        thread_pool: ThreadPoolManager | None = None,
    ) -> None:
        self._rag = rag_service
        self._thread_pool = thread_pool

    def _get_pool(self) -> ThreadPoolManager:
        """获取线程池实例。"""
        if self._thread_pool is None:
            from src.ai.utils.thread_pool import get_thread_pool

            self._thread_pool = get_thread_pool()
        return self._thread_pool

    # ── 索引 ──────────────────────────────────────────────────

    async def index_file(
        self,
        path: str,
        *,
        session_id: str | None = None,
        reindex: bool = False,
    ) -> dict[str, Any]:
        """索引文件。

        Args:
            path: 文件路径。
            session_id: 会话 ID（可选）。
            reindex: 是否强制重新索引。

        Returns:
            索引结果信息。
        """
        return await self._get_pool().run_io(
            self._rag.aindex_file, path, session_id=session_id
        )

    async def index_url(
        self,
        url: str,
        *,
        session_id: str | None = None,
        reindex: bool = False,
    ) -> dict[str, Any]:
        """索引 URL。

        Args:
            url: 目标 URL。
            session_id: 会话 ID（可选）。

        Returns:
            索引结果信息。
        """
        return await self._get_pool().run_io(
            self._rag.aindex_url, url, session_id=session_id
        )

    async def index_text(
        self,
        text: str,
        *,
        title: str | None = None,
        session_id: str | None = None,
        reindex: bool = False,
    ) -> dict[str, Any]:
        """索引文本。

        Args:
            text: 文本内容。
            title: 文档标题（可选）。
            session_id: 会话 ID（可选）。

        Returns:
            索引结果信息。
        """
        return await self._get_pool().run_io(
            self._rag.aindex_text, text, title=title, session_id=session_id
        )

    async def index_directory(
        self,
        path: str,
        *,
        patterns: list[str] | None = None,
        session_id: str | None = None,
        reindex: bool = False,
    ) -> list[dict[str, Any]]:
        """索引目录。

        Args:
            path: 目录路径。
            patterns: 文件匹配模式。
            session_id: 会话 ID（可选）。

        Returns:
            索引结果列表。
        """
        return await self._get_pool().run_io(
            self._rag.aindex_directory, path, patterns=patterns, session_id=session_id
        )

    # ── 检索 ──────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        *,
        session_id: str | None = None,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """向量相似度搜索。

        Args:
            query: 搜索查询。
            session_id: 会话 ID（可选）。
            top_k: 返回结果数量。

        Returns:
            搜索结果列表。
        """
        result = await self._get_pool().run_io(
            self._rag.asearch, query, session_id=session_id, top_k=top_k
        )
        return self._search_result_to_dicts(result)

    async def hybrid_search(
        self,
        query: str,
        *,
        session_id: str | None = None,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """混合搜索（向量 + BM25）。

        Args:
            query: 搜索查询。
            session_id: 会话 ID（可选）。
            top_k: 返回结果数量。

        Returns:
            搜索结果列表。
        """
        result = await self._get_pool().run_io(
            self._rag.ahybrid_search, query, session_id=session_id, top_k=top_k
        )
        return self._search_result_to_dicts(result)

    # ── 文档管理 ──────────────────────────────────────────────

    async def delete_file(
        self,
        path: str,
        *,
        session_id: str | None = None,
    ) -> bool:
        """删除文件索引。

        Args:
            path: 文件路径。
            session_id: 会话 ID（可选）。

        Returns:
            是否删除成功。
        """
        return await self._get_pool().run_io(
            self._rag.adelete_file, path, session_id=session_id
        )

    async def delete_all(
        self,
        *,
        session_id: str | None = None,
    ) -> int:
        """删除全部文档索引。

        Args:
            session_id: 会话 ID（可选）。

        Returns:
            删除的文档数量。
        """
        return await self._get_pool().run_io(
            self._rag.adelete_all, session_id=session_id
        )

    async def list_documents(
        self,
        *,
        session_id: str | None = None,
        status: str | None = "active",
    ) -> list[dict[str, Any]]:
        """列出已索引的文档。

        Args:
            session_id: 会话 ID（可选）。
            status: 文档状态过滤。

        Returns:
            文档信息列表。
        """
        docs = await self._get_pool().run_io(
            self._rag.alist_documents, session_id=session_id
        )
        results: list[dict[str, Any]] = []
        for doc in docs:
            doc_dict = {
                "source_path": doc.source_path,
                "title": doc.title,
                "chunk_count": doc.chunk_count,
                "mime_type": doc.mime_type,
                "session_id": doc.session_id,
                "scope": doc.scope,
                "collection_name": doc.collection_name,
                "status": doc.status,
                "content_hash": doc.content_hash,
            }
            if status is None or doc_dict["status"] == status:
                results.append(doc_dict)
        return results

    async def get_stats(
        self,
        *,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """获取 RAG 统计信息。

        Args:
            session_id: 会话 ID（可选）。

        Returns:
            统计信息字典。
        """
        return await self._get_pool().run_io(
            self._rag.aget_stats, session_id=session_id
        )

    # ── 内部工具 ──────────────────────────────────────────────

    @staticmethod
    def _search_result_to_dicts(result: Any) -> list[dict[str, Any]]:
        """将搜索结果转换为字典列表。"""
        items: list[dict[str, Any]] = []
        raw = getattr(result, "raw_results", [])
        for i, doc in enumerate(raw):
            items.append(
                {
                    "id": getattr(doc, "id", str(i)),
                    "source_path": getattr(doc, "metadata", {}).get("source_path", ""),
                    "title": getattr(doc, "metadata", {}).get("title", ""),
                    "content": getattr(doc, "page_content", ""),
                    "chunk_index": i,
                    "score": getattr(doc, "metadata", {}).get("score", 0.0),
                }
            )
        return items
