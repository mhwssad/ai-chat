"""RAG 索引和检索服务 — 基于 langchain-chroma，支持会话隔离。"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from sqlmodel import Session

from src.ai.config.base_config import project_root
from src.ai.core.rag.loaders.base import LoaderStrategy
from src.ai.core.rag.splitters.base import SplitChunk, SplitterStrategy
from src.ai.exception.rag_exception import RagError
from src.ai.storage.runtime_repository import RagDocumentRepository

if TYPE_CHECKING:
    from src.ai.config.settings import Settings
    from src.ai.core.prompts.service import PromptService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RagSearchResult:
    """向量搜索结果。"""

    id: str
    source_path: str
    title: str
    content: str
    chunk_index: int
    score: float


@dataclass(frozen=True)
class RagDocumentInfo:
    """已索引文件摘要。"""

    source_path: str
    title: str
    chunk_count: int
    mime_type: str
    session_id: str | None = None
    scope: str = "global"
    collection_name: str = ""
    status: str = "active"
    content_hash: str | None = None


class ChromaStore:
    """Chroma 向量存储包装类，封装 langchain-chroma 私有属性访问。

    提供公共接口替代直接访问 store._client、store._collection 等私有属性，
    避免 langchain-chroma 版本升级导致的兼容性问题。

    Args:
        store: langchain_chroma.Chroma 实例。
    """

    def __init__(self, store: Chroma) -> None:
        self._store = store

    @property
    def store(self) -> Chroma:
        """获取底层 Chroma 实例。"""
        return self._store

    @property
    def collection_name(self) -> str:
        """获取 collection 名称。"""
        return self._store._collection.name

    def list_collections(self) -> list[str]:
        """列出所有 collection 名称。"""
        return self._store._client.list_collections()  # type: ignore[return-value]

    def delete_collection(self, name: str) -> None:
        """删除指定 collection。"""
        self._store._client.delete_collection(name)

    def get(self, **kwargs) -> dict:
        """代理底层 store.get()。"""
        return self._store.get(**kwargs)

    def delete(self, **kwargs) -> None:
        """代理底层 store.delete()。"""
        self._store.delete(**kwargs)

    def add_documents(self, **kwargs) -> None:
        """代理底层 store.add_documents()。"""
        self._store.add_documents(**kwargs)

    def similarity_search_with_score(self, query: str, k: int = 4) -> list:
        """代理底层 store.similarity_search_with_score()。"""
        return self._store.similarity_search_with_score(query, k=k)


class RagService:
    """基于 langchain-chroma 的文件索引、向量存储和相似度检索。

    所有依赖（Embeddings、Loader、Splitter）通过构造函数注入，
    不在类内部创建任何具体依赖。

    支持增量索引（基于 content_hash）和混合检索（向量 + BM25）。
    """

    def __init__(
        self,
        *,
        embeddings: Embeddings,
        loader: LoaderStrategy,
        splitter: SplitterStrategy,
        persist_directory: str | Path,
        collection_name: str,
        top_k: int = 5,
        settings: Settings,
        prompt_service: PromptService,
        meta_store: object | None = None,
        bm25_retriever: object | None = None,
        thread_pool: object | None = None,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        self._embeddings = embeddings
        self._loader = loader
        self._splitter = splitter
        self._persist_dir = str(persist_directory)
        self._base_collection = collection_name
        self._top_k = top_k
        self._settings = settings
        self._prompt_service = prompt_service
        self._stores: dict[str, ChromaStore] = {}
        self._meta_store = meta_store
        self._bm25 = bm25_retriever
        self._bm25_dirty = True
        self._thread_pool = thread_pool
        self._session_factory = session_factory

    # ── 向量存储 ──────────────────────────────────────────

    def _get_store(self, session_id: str | None = None) -> ChromaStore:
        """获取（或创建）向量存储实例。

        Args:
            session_id: 会话 ID，非空时使用会话级 collection。

        Returns:
            ChromaStore 包装实例。
        """
        collection = (
            f"{self._base_collection}_{session_id}"
            if session_id
            else self._base_collection
        )
        if collection not in self._stores:
            chroma = Chroma(
                collection_name=collection,
                embedding_function=self._embeddings,
                persist_directory=self._persist_dir,
            )
            self._stores[collection] = ChromaStore(chroma)
        return self._stores[collection]

    # ── 索引 ──────────────────────────────────────────────

    def index_file(
        self,
        path: str | Path,
        *,
        session_id: str | None = None,
        reindex: bool = False,
    ) -> RagDocumentInfo:
        """索引文件：加载 → 切分 → 写入 Chroma（自动 embedding）。"""
        source_path = _normalize_source_path(path, force_path=True)

        # 增量检查：mtime + file_size 快速判断
        if not reindex and self._meta_store is not None:
            file_path = Path(source_path)
            if file_path.is_file():
                meta = self._meta_store.get(source_path)  # type: ignore[attr-defined]
                if meta is not None:
                    stat = file_path.stat()
                    if (
                        meta.file_size == stat.st_size
                        and abs(meta.mtime - stat.st_mtime) < 0.01
                    ):
                        info = RagDocumentInfo(
                            source_path=source_path,
                            title=meta.chunk_ids[0].split("#")[0]
                            if meta.chunk_ids
                            else "",
                            chunk_count=meta.chunk_count,
                            mime_type="",
                            session_id=session_id,
                            scope=_scope_for(session_id),
                            collection_name=self._get_store(session_id).collection_name,
                            status="active",
                            content_hash=meta.content_hash,
                        )
                        self._sync_document_record(info)
                        return info

        loaded_docs = self._loader.load_file(path)
        return self._index_documents(
            loaded_docs,
            source_path=source_path,
            session_id=session_id,
            reindex=reindex,
        )

    def index_url(
        self,
        url: str,
        *,
        session_id: str | None = None,
        reindex: bool = False,
    ) -> RagDocumentInfo:
        """从 URL 下载并索引文档。"""
        from src.ai.core.rag.loaders.url_loader import UrlLoader

        url_loader = UrlLoader(self._loader)  # type: ignore[arg-type]
        loaded_docs = url_loader.load_url(url)
        return self._index_documents(
            loaded_docs,
            source_path=url,
            session_id=session_id,
            reindex=reindex,
        )

    def index_stream(
        self,
        data: bytes,
        *,
        mime_type: str | None = None,
        filename: str | None = None,
        session_id: str | None = None,
        reindex: bool = False,
    ) -> RagDocumentInfo:
        """从字节流索引文档。"""
        from src.ai.core.rag.loaders.stream_loader import StreamLoader

        stream_loader = StreamLoader(self._loader)  # type: ignore[arg-type]
        loaded_docs = stream_loader.load_stream(
            data, mime_type=mime_type, filename=filename
        )
        source_path = filename or "stream"
        return self._index_documents(
            loaded_docs,
            source_path=source_path,
            session_id=session_id,
            reindex=reindex,
        )

    def index_text(
        self,
        text: str,
        *,
        title: str | None = None,
        session_id: str | None = None,
        reindex: bool = False,
    ) -> RagDocumentInfo:
        """直接索引原始文本。"""
        doc = Document(
            page_content=text,
            metadata={
                "source": "text",
                "title": title or "text",
                "mime_type": "text/plain",
                "size_bytes": len(text.encode("utf-8")),
            },
        )
        source_path = f"text:{title or 'untitled'}"
        return self._index_documents(
            [doc],
            source_path=source_path,
            session_id=session_id,
            reindex=reindex,
        )

    def _index_documents(
        self,
        loaded_docs: list[Document],
        *,
        source_path: str,
        session_id: str | None = None,
        reindex: bool = False,
    ) -> RagDocumentInfo:
        """通用索引逻辑：切分 → 增量检查 → 写入 Chroma。"""
        store = self._get_store(session_id)

        # 1. 切分
        all_chunks: list[tuple[Document, SplitChunk]] = []
        for doc in loaded_docs:
            chunks = self._splitter.split_document(doc)
            for chunk in chunks:
                all_chunks.append((doc, chunk))

        if not all_chunks:
            raise RagError(f"文档切分结果为空: {source_path}")

        # 2. 计算 content_hash
        content_hash = _sha256("".join(d.page_content for d in loaded_docs))

        # 3. 增量检查（基于 content_hash）
        if self._meta_store is not None and not reindex:
            existing_meta = self._meta_store.get(source_path)  # type: ignore[attr-defined]
            if existing_meta is not None and existing_meta.content_hash == content_hash:
                logger.debug("文件未变化，跳过索引: %s", source_path)
                info = self._make_doc_info(
                    source_path,
                    loaded_docs[0],
                    existing_meta.chunk_count,
                    session_id=session_id,
                    collection_name=store.collection_name,
                    content_hash=content_hash,
                )
                self._sync_document_record(info)
                return info

        # 4. 删除旧数据
        existing = store.get(where={"source_path": source_path})
        if existing["ids"]:
            store.delete(ids=existing["ids"])

        # 5. 构建 LangChain Document 列表
        ids: list[str] = []
        documents: list[Document] = []
        for doc, chunk in all_chunks:
            chunk_id = f"{content_hash}#{chunk.index}"
            ids.append(chunk_id)
            metadata = {
                **doc.metadata,
                "source_path": source_path,
                "session_id": session_id or "",
                "scope": _scope_for(session_id),
                "collection_name": store.collection_name,
                "chunk_index": chunk.index,
                "content_hash": content_hash,
                **chunk.metadata,
            }
            documents.append(Document(page_content=chunk.content, metadata=metadata))

        # 6. 写入 Chroma
        store.add_documents(documents=documents, ids=ids)

        # 7. 更新元数据
        if self._meta_store is not None:
            from src.ai.core.rag.index_meta import IndexedFileMeta
            from datetime import datetime, timezone

            file_size = 0
            mtime = 0.0
            file_path = Path(source_path)
            if file_path.is_file():
                stat = file_path.stat()
                file_size = stat.st_size
                mtime = stat.st_mtime

            self._meta_store.put(  # type: ignore[attr-defined]
                IndexedFileMeta(
                    source_path=source_path,
                    content_hash=content_hash,
                    chunk_ids=ids,
                    chunk_count=len(all_chunks),
                    indexed_at=datetime.now(timezone.utc).isoformat(),
                    file_size=file_size,
                    mtime=mtime,
                )
            )

        # 8. 标记 BM25 索引需要重建
        self._bm25_dirty = True

        info = self._make_doc_info(
            source_path,
            loaded_docs[0],
            len(all_chunks),
            session_id=session_id,
            collection_name=store.collection_name,
            content_hash=content_hash,
        )
        self._sync_document_record(info)
        return info

    def index_directory(
        self,
        path: str | Path,
        *,
        session_id: str | None = None,
        patterns: list[str] | None = None,
        reindex: bool = False,
    ) -> list[RagDocumentInfo]:
        """批量索引目录。"""
        root = Path(path)
        if not root.is_dir():
            raise RagError(f"目录不存在: {path}")

        patterns = patterns or [
            p.strip()
            for p in self._get_settings().rag.rag_index_patterns.split(",")
            if p.strip()
        ]
        documents: list[RagDocumentInfo] = []
        for pattern in patterns:
            for file_path in root.glob(pattern):
                if file_path.is_file():
                    try:
                        doc = self.index_file(
                            file_path,
                            session_id=session_id,
                            reindex=reindex,
                        )
                        documents.append(doc)
                    except Exception:
                        logger.warning("索引文件失败: %s", file_path, exc_info=True)
        return documents

    # ── 检索 ──────────────────────────────────────────────

    def search(
        self,
        query: str,
        *,
        session_id: str | None = None,
        top_k: int | None = None,
    ) -> list[RagSearchResult]:
        """向量相似度搜索。"""
        store = self._get_store(session_id)
        k = top_k if top_k is not None else self._top_k

        results_with_scores = store.similarity_search_with_score(query, k=k)

        output: list[RagSearchResult] = []
        for doc, distance in results_with_scores:
            meta = doc.metadata
            output.append(
                RagSearchResult(
                    id=meta.get("content_hash", "")
                    + "#"
                    + str(meta.get("chunk_index", 0)),
                    source_path=meta.get("source_path", ""),
                    title=meta.get("title", ""),
                    content=doc.page_content,
                    chunk_index=meta.get("chunk_index", 0),
                    score=1.0 - distance,
                )
            )
        return output

    def hybrid_search(
        self,
        query: str,
        *,
        session_id: str | None = None,
        top_k: int | None = None,
    ) -> list[RagSearchResult]:
        """混合检索：向量检索 + BM25 关键词检索，RRF 融合。

        Args:
            query: 查询文本。
            session_id: 会话 ID。
            top_k: 返回结果数量。

        Returns:
            融合后的检索结果。
        """
        k = top_k if top_k is not None else self._top_k

        # 向量检索
        vector_results = self.search(query, session_id=session_id, top_k=k * 2)

        # BM25 检索（如果可用）
        bm25_results: list[RagSearchResult] = []
        if self._bm25 is not None:
            self._ensure_bm25_index(session_id)
            if self._bm25.is_built:  # type: ignore[attr-defined]
                raw_bm25 = self._bm25.search(query, top_k=k * 2)  # type: ignore[attr-defined]
                for r in raw_bm25:
                    meta = r.metadata
                    bm25_results.append(
                        RagSearchResult(
                            id=r.doc_id,
                            source_path=meta.get("source_path", ""),
                            title=meta.get("title", ""),
                            content=r.content,
                            chunk_index=meta.get("chunk_index", 0),
                            score=r.score,
                        )
                    )

        if not bm25_results:
            return vector_results[:k]

        # RRF 融合
        return self._rrf_merge(vector_results, bm25_results, top_k=k)

    def _ensure_bm25_index(self, session_id: str | None = None) -> None:
        """确保 BM25 索引已构建（惰性重建）。"""
        if not self._bm25_dirty and self._bm25.is_built:  # type: ignore[union-attr]
            return

        store = self._get_store(session_id)
        all_data = store.get()
        if not all_data["ids"]:
            return

        doc_ids = all_data["ids"]
        contents = [d for d in all_data["documents"]]
        metadata_list = all_data["metadatas"]

        self._bm25.build_index(doc_ids, contents, metadata_list)  # type: ignore[union-attr]
        self._bm25_dirty = False

    @staticmethod
    def _rrf_merge(
        vector_results: list[RagSearchResult],
        bm25_results: list[RagSearchResult],
        top_k: int = 5,
        k: int = 60,
    ) -> list[RagSearchResult]:
        """Reciprocal Rank Fusion 融合两路检索结果。

        Args:
            vector_results: 向量检索结果。
            bm25_results: BM25 检索结果。
            top_k: 返回结果数量。
            k: RRF 参数 k（默认 60）。

        Returns:
            融合后的结果。
        """
        scores: dict[str, float] = {}
        id_to_result: dict[str, RagSearchResult] = {}

        for rank, r in enumerate(vector_results):
            scores[r.id] = scores.get(r.id, 0.0) + 1.0 / (k + rank + 1)
            id_to_result[r.id] = r

        for rank, r in enumerate(bm25_results):
            scores[r.id] = scores.get(r.id, 0.0) + 1.0 / (k + rank + 1)
            id_to_result[r.id] = r

        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        results: list[RagSearchResult] = []
        for doc_id in sorted_ids[:top_k]:
            original = id_to_result[doc_id]
            results.append(
                RagSearchResult(
                    id=original.id,
                    source_path=original.source_path,
                    title=original.title,
                    content=original.content,
                    chunk_index=original.chunk_index,
                    score=scores[doc_id],
                )
            )
        return results

    def build_context(
        self,
        query: str,
        *,
        session_id: str | None = None,
        top_k: int | None = None,
    ) -> str:
        """将搜索结果格式化为 LLM 上下文文本。"""
        results = self.search(query, session_id=session_id, top_k=top_k)
        if not results:
            return ""

        prepared = [
            {"index": i, "title": r.title or r.source_path, "content": r.content}
            for i, r in enumerate(results, start=1)
        ]

        from src.ai.core.prompts.types import PromptRenderRequest

        rendered = self._prompt_service.render(
            PromptRenderRequest(
                prompt_key="rag.context_format",
                variables={"results": prepared},
            )
        )
        return rendered.content

    # ── 删除 ──────────────────────────────────────────────

    # ── 更新 ──────────────────────────────────────────────

    def update_text(
        self,
        text: str,
        *,
        source_path: str,
        title: str | None = None,
        session_id: str | None = None,
    ) -> RagDocumentInfo:
        """更新已索引的文本内容（先删后建）。

        Args:
            text: 新的文本内容。
            source_path: 原索引的 source_path。
            title: 文档标题。
            session_id: 会话 ID。

        Returns:
            更新后的文档信息。
        """
        self.delete_file(source_path, session_id=session_id)
        return self.index_text(
            text,
            title=title or source_path,
            session_id=session_id,
            reindex=True,
        )

    def get_document_chunks(
        self,
        source_path: str,
        *,
        session_id: str | None = None,
    ) -> list[dict]:
        """获取指定文档的所有 chunks 详情。

        Args:
            source_path: 文档的 source_path。
            session_id: 会话 ID。

        Returns:
            分块详情列表。
        """
        store = self._get_store(session_id)
        existing = store.get(where={"source_path": source_path})
        if not existing["ids"]:
            return []

        chunks: list[dict] = []
        for i, doc_id in enumerate(existing["ids"]):
            meta = existing["metadatas"][i] if existing["metadatas"] else {}
            content = existing["documents"][i] if existing["documents"] else ""
            chunks.append(
                {
                    "id": doc_id,
                    "content": content,
                    "chunk_index": meta.get("chunk_index", i),
                    "metadata": meta,
                }
            )
        return chunks

    def get_all_stats(self) -> dict:
        """获取全局统计（跨所有会话）。

        Returns:
            包含 default_chunks、sessions、total_sessions、total_chunks 的字典。
        """
        # 默认知识库统计
        default_stats = self.get_stats()
        default_chunks = default_stats["total_chunks"]

        # 会话级知识库统计
        sessions: list[dict] = []
        for session_id in self.list_sessions():
            session_stats = self.get_stats(session_id=session_id)
            docs = self.list_documents(session_id=session_id)
            sessions.append(
                {
                    "session_id": session_id,
                    "document_count": len(docs),
                    "total_chunks": session_stats["total_chunks"],
                }
            )

        total_chunks = default_chunks + sum(s["total_chunks"] for s in sessions)
        return {
            "default_chunks": default_chunks,
            "sessions": sessions,
            "total_sessions": len(sessions),
            "total_chunks": total_chunks,
        }

    def delete_documents_batch(
        self,
        paths: list[str],
        *,
        session_id: str | None = None,
    ) -> dict[str, bool]:
        """批量删除多个文档。

        Args:
            paths: 文件路径列表。
            session_id: 会话 ID。

        Returns:
            每个路径的删除结果。
        """
        results: dict[str, bool] = {}
        for path in paths:
            results[path] = self.delete_file(path, session_id=session_id)
        return results

    # ── 删除 ──────────────────────────────────────────────

    def delete_file(
        self,
        path: str | Path,
        *,
        session_id: str | None = None,
    ) -> bool:
        """删除文件的所有 chunk。"""
        source_path = _normalize_source_path(path)
        store = self._get_store(session_id)
        existing = store.get(where={"source_path": source_path})
        if not existing["ids"]:
            return False
        store.delete(ids=existing["ids"])

        # 更新元数据
        if self._meta_store is not None:
            self._meta_store.delete(source_path)  # type: ignore[attr-defined]

        self._set_document_status(source_path, session_id=session_id, status="deleted")
        self._bm25_dirty = True
        return True

    def delete_all(self, *, session_id: str | None = None) -> int:
        """清空指定 collection 的所有数据。"""
        store = self._get_store(session_id)
        all_data = store.get()
        count = len(all_data["ids"]) if all_data["ids"] else 0
        if count > 0:
            store.delete(ids=all_data["ids"])
        self._mark_scope_documents_deleted(session_id=session_id)
        self._bm25_dirty = True
        return count

    # ── 会话管理 ──────────────────────────────────────────

    def list_sessions(self) -> list[str]:
        """列出所有会话级知识库的 session_id。"""
        store = self._get_store()
        prefix = f"{self._base_collection}_"
        sessions: list[str] = []
        for name in store.list_collections():
            if name.startswith(prefix):
                sessions.append(name[len(prefix) :])
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """删除会话级知识库。"""
        collection_name = f"{self._base_collection}_{session_id}"
        if collection_name in self._stores:
            del self._stores[collection_name]
        store = self._get_store()
        try:
            store.delete_collection(collection_name)
            self._mark_scope_documents_deleted(session_id=session_id)
            self._bm25_dirty = True
            return True
        except Exception:
            logger.warning(
                "删除会话 collection 失败: %s", collection_name, exc_info=True
            )
            return False

    # ── 查询 ──────────────────────────────────────────────

    def list_documents(
        self,
        *,
        session_id: str | None = None,
        status: str | None = "active",
    ) -> list[RagDocumentInfo]:
        """列出文档元信息，合并 Chroma 实际索引与 DB 控制面状态。"""
        store = self._get_store(session_id)
        all_data = store.get()

        seen: dict[str, RagDocumentInfo] = {}
        for meta in all_data["metadatas"] or []:
            sp = meta.get("source_path", "")
            if sp and sp not in seen:
                seen[sp] = RagDocumentInfo(
                    source_path=sp,
                    title=meta.get("title", ""),
                    chunk_count=0,
                    mime_type=meta.get("mime_type", ""),
                    session_id=session_id,
                    scope=meta.get("scope") or _scope_for(session_id),
                    collection_name=meta.get("collection_name") or store.collection_name,
                    status="active",
                    content_hash=meta.get("content_hash"),
                )
            if sp in seen:
                seen[sp] = replace(seen[sp], chunk_count=seen[sp].chunk_count + 1)
        return self._apply_document_state(
            list(seen.values()),
            session_id=session_id,
            status=status,
        )

    def get_stats(self, *, session_id: str | None = None) -> dict:
        """返回向量库统计信息。"""
        store = self._get_store(session_id)
        all_data = store.get()
        total = len(all_data["ids"]) if all_data["ids"] else 0
        return {
            "total_chunks": total,
            "collection_name": store.collection_name,
        }

    # ── 异步包装（线程池执行同步 IO） ──────────────────────────

    def _get_pool(self):
        """获取线程池实例。"""
        if self._thread_pool is None:
            from src.ai.utils.thread_pool import get_thread_pool

            self._thread_pool = get_thread_pool()
        return self._thread_pool

    async def aindex_file(
        self,
        path: str | Path,
        *,
        session_id: str | None = None,
        reindex: bool = False,
    ) -> RagDocumentInfo:
        """异步索引文件。"""
        return await self._get_pool().run_io(
            self.index_file, path, session_id=session_id, reindex=reindex
        )

    async def aindex_directory(
        self,
        path: str | Path,
        *,
        session_id: str | None = None,
        patterns: list[str] | None = None,
        reindex: bool = False,
    ) -> list[RagDocumentInfo]:
        """异步批量索引目录。"""
        return await self._get_pool().run_io(
            self.index_directory,
            path,
            session_id=session_id,
            patterns=patterns,
            reindex=reindex,
        )

    async def aindex_url(
        self,
        url: str,
        *,
        session_id: str | None = None,
        reindex: bool = False,
    ) -> RagDocumentInfo:
        """异步从 URL 下载并索引文档。"""
        return await self._get_pool().run_io(
            self.index_url, url, session_id=session_id, reindex=reindex
        )

    async def aindex_stream(
        self,
        data: bytes,
        *,
        mime_type: str | None = None,
        filename: str | None = None,
        session_id: str | None = None,
        reindex: bool = False,
    ) -> RagDocumentInfo:
        """异步从字节流索引文档。"""
        return await self._get_pool().run_io(
            self.index_stream,
            data,
            mime_type=mime_type,
            filename=filename,
            session_id=session_id,
            reindex=reindex,
        )

    async def aindex_text(
        self,
        text: str,
        *,
        title: str | None = None,
        session_id: str | None = None,
        reindex: bool = False,
    ) -> RagDocumentInfo:
        """异步直接索引原始文本。"""
        return await self._get_pool().run_io(
            self.index_text,
            text,
            title=title,
            session_id=session_id,
            reindex=reindex,
        )

    async def asearch(
        self,
        query: str,
        *,
        session_id: str | None = None,
        top_k: int | None = None,
    ) -> list[RagSearchResult]:
        """异步向量相似度搜索。"""
        return await self._get_pool().run_io(
            self.search, query, session_id=session_id, top_k=top_k
        )

    async def ahybrid_search(
        self,
        query: str,
        *,
        session_id: str | None = None,
        top_k: int | None = None,
    ) -> list[RagSearchResult]:
        """异步混合检索。"""
        return await self._get_pool().run_io(
            self.hybrid_search, query, session_id=session_id, top_k=top_k
        )

    async def abuild_context(
        self,
        query: str,
        *,
        session_id: str | None = None,
        top_k: int | None = None,
    ) -> str:
        """异步将搜索结果格式化为 LLM 上下文。"""
        return await self._get_pool().run_io(
            self.build_context, query, session_id=session_id, top_k=top_k
        )

    async def alist_documents(
        self, *, session_id: str | None = None, status: str | None = "active"
    ) -> list[RagDocumentInfo]:
        """异步列出所有已索引文件。"""
        return await self._get_pool().run_io(
            self.list_documents,
            session_id=session_id,
            status=status,
        )

    async def adelete_file(
        self, path: str | Path, *, session_id: str | None = None
    ) -> bool:
        """异步删除文件的所有 chunk。"""
        return await self._get_pool().run_io(
            self.delete_file, path, session_id=session_id
        )

    async def adelete_all(self, *, session_id: str | None = None) -> int:
        """异步清空指定 collection 的所有数据。"""
        return await self._get_pool().run_io(self.delete_all, session_id=session_id)

    async def aget_stats(self, *, session_id: str | None = None) -> dict:
        """异步获取向量库统计信息。"""
        return await self._get_pool().run_io(self.get_stats, session_id=session_id)

    async def alist_sessions(self) -> list[str]:
        """异步列出所有会话级知识库。"""
        return await self._get_pool().run_io(self.list_sessions)

    async def aget_all_stats(self) -> dict:
        """异步获取全局统计。"""
        return await self._get_pool().run_io(self.get_all_stats)

    async def aupdate_text(
        self,
        text: str,
        *,
        source_path: str,
        title: str | None = None,
        session_id: str | None = None,
    ) -> RagDocumentInfo:
        """异步更新已索引的文本内容。"""
        return await self._get_pool().run_io(
            self.update_text,
            text,
            source_path=source_path,
            title=title,
            session_id=session_id,
        )

    # ── 内部 ──────────────────────────────────────────────

    def _get_settings(self):
        """获取配置。"""
        return self._settings

    def _make_doc_info(
        self,
        source_path: str,
        doc: Document,
        chunk_count: int,
        *,
        session_id: str | None = None,
        collection_name: str | None = None,
        content_hash: str | None = None,
    ) -> RagDocumentInfo:
        """从加载结果构建文件摘要。"""
        meta = doc.metadata if doc.metadata else {}
        return RagDocumentInfo(
            source_path=source_path,
            title=meta.get("title", ""),
            chunk_count=chunk_count,
            mime_type=meta.get("mime_type", ""),
            session_id=session_id,
            scope=_scope_for(session_id),
            collection_name=collection_name or self._get_store(session_id).collection_name,
            status="active",
            content_hash=content_hash,
        )

    def _sync_document_record(self, info: RagDocumentInfo) -> None:
        """同步 RAG 文档控制面元信息。"""
        if self._session_factory is None:
            return
        try:
            with self._session_factory() as session:
                repo = RagDocumentRepository(session)
                record = repo.get_by_source(info.source_path, session_id=info.session_id)
                payload = {
                    "session_id": info.session_id,
                    "scope": info.scope,
                    "collection_name": info.collection_name,
                    "source_path": info.source_path,
                    "title": info.title,
                    "mime_type": info.mime_type,
                    "content_hash": info.content_hash,
                    "chunk_count": info.chunk_count,
                    "status": info.status,
                    "extra": json.dumps(
                        {
                            "source_path": info.source_path,
                            "scope": info.scope,
                        },
                        ensure_ascii=False,
                    ),
                }
                if record is None:
                    repo.create(**payload)
                else:
                    repo.update(record, **payload)
                session.commit()
        except Exception:
            logger.debug("同步 RAG 文档控制面失败: %s", info.source_path, exc_info=True)

    def _set_document_status(
        self,
        source_path: str,
        *,
        session_id: str | None,
        status: str,
    ) -> None:
        """更新单个 RAG 文档控制面状态。"""
        if self._session_factory is None:
            return
        try:
            with self._session_factory() as session:
                repo = RagDocumentRepository(session)
                record = repo.get_by_source(source_path, session_id=session_id)
                if record is not None:
                    repo.update(record, status=status, chunk_count=0)
                    session.commit()
        except Exception:
            logger.debug("更新 RAG 文档状态失败: %s", source_path, exc_info=True)

    def _mark_scope_documents_deleted(self, *, session_id: str | None = None) -> None:
        """将指定作用域下的 RAG 文档标记为已删除。"""
        if self._session_factory is None:
            return
        try:
            with self._session_factory() as session:
                repo = RagDocumentRepository(session)
                records = repo.list(
                    limit=10000,
                    order_by="updated_at",
                    descending=True,
                    session_id=session_id,
                )
                for record in records:
                    repo.update(record, status="deleted", chunk_count=0)
                session.commit()
        except Exception:
            logger.debug("批量更新 RAG 文档状态失败", exc_info=True)

    def _apply_document_state(
        self,
        docs: list[RagDocumentInfo],
        *,
        session_id: str | None,
        status: str | None,
    ) -> list[RagDocumentInfo]:
        """将 DB 控制面状态合并到 Chroma 文档列表。"""
        if self._session_factory is None:
            return [
                doc
                for doc in docs
                if status is None or doc.status == status
            ]

        try:
            with self._session_factory() as session:
                rows = RagDocumentRepository(session).list(
                    limit=10000,
                    order_by="updated_at",
                    descending=True,
                    session_id=session_id,
                )
        except Exception:
            logger.debug("读取 RAG 文档控制面失败", exc_info=True)
            rows = []

        state = {row.source_path: row for row in rows}
        merged: dict[str, RagDocumentInfo] = {}
        for doc in docs:
            row = state.get(doc.source_path)
            if row is None:
                merged[doc.source_path] = doc
                continue
            merged[doc.source_path] = replace(
                doc,
                title=row.title or doc.title,
                mime_type=row.mime_type or doc.mime_type,
                session_id=row.session_id,
                scope=row.scope,
                collection_name=row.collection_name or doc.collection_name,
                status=row.status,
                content_hash=row.content_hash or doc.content_hash,
            )

        for row in rows:
            if row.source_path in merged or row.status == "active":
                continue
            merged[row.source_path] = RagDocumentInfo(
                source_path=row.source_path,
                title=row.title or "",
                chunk_count=row.chunk_count,
                mime_type=row.mime_type or "",
                session_id=row.session_id,
                scope=row.scope,
                collection_name=row.collection_name,
                status=row.status,
                content_hash=row.content_hash,
            )

        result = list(merged.values())
        if status is not None:
            result = [doc for doc in result if doc.status == status]
        return result


def _sha256(text: str) -> str:
    """计算文本 SHA-256 哈希。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _scope_for(session_id: str | None) -> str:
    """根据 session_id 生成 RAG 文档作用域。"""
    return "session" if session_id else "global"


def _normalize_source_path(path: str | Path, *, force_path: bool = False) -> str:
    """归一化 RAG 来源路径，避免把 URL 和 text source 错当文件路径。"""
    raw = str(path)
    lower = raw.lower()
    if not force_path and (
        lower.startswith("text:")
        or lower.startswith("http://")
        or lower.startswith("https://")
    ):
        return raw
    path_obj = Path(raw)
    if force_path or path_obj.is_absolute() or path_obj.exists() or len(path_obj.parts) > 1:
        return str(path_obj.resolve())
    return raw


def create_rag_service(
    *,
    embeddings: Embeddings,
    loader: LoaderStrategy,
    splitter: SplitterStrategy,
    settings: Settings,
    prompt_service: PromptService,
) -> RagService:
    """工厂函数：创建 RagService。"""
    rag = settings.rag

    return RagService(
        embeddings=embeddings,
        loader=loader,
        splitter=splitter,
        persist_directory=project_root / rag.rag_persist_dir,
        collection_name=rag.rag_collection_name,
        top_k=rag.rag_top_k,
        settings=settings,
        prompt_service=prompt_service,
    )
