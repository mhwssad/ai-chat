"""RAG 索引和检索服务 — 基于 langchain-chroma，支持会话隔离。"""

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.ai.config.base_config import project_root
from src.ai.core.rag.loaders.base import LoaderStrategy
from src.ai.core.rag.splitters.base import SplitChunk, SplitterStrategy
from src.ai.exception.rag_exception import RagError

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


class RagService:
    """基于 langchain-chroma 的文件索引、向量存储和相似度检索。

    所有依赖（Embeddings、Loader、Splitter）通过构造函数注入，
    不在类内部创建任何具体依赖。
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
        settings: object,
        prompt_service: object,
    ) -> None:
        self._embeddings = embeddings
        self._loader = loader
        self._splitter = splitter
        self._persist_dir = str(persist_directory)
        self._base_collection = collection_name
        self._top_k = top_k
        self._settings = settings
        self._prompt_service = prompt_service
        self._stores: dict[str, Chroma] = {}

    # ── 向量存储 ──────────────────────────────────────────

    def _get_store(self, session_id: str | None = None) -> Chroma:
        """获取（或创建）向量存储实例。

        Args:
            session_id: 会话 ID，非空时使用会话级 collection。

        Returns:
            Chroma 向量存储。
        """
        collection = (
            f"{self._base_collection}_{session_id}"
            if session_id
            else self._base_collection
        )
        if collection not in self._stores:
            self._stores[collection] = Chroma(
                collection_name=collection,
                embedding_function=self._embeddings,
                persist_directory=self._persist_dir,
            )
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
        source_path = str(Path(path).resolve())
        store = self._get_store(session_id)

        # 1. 加载
        loaded_docs = self._loader.load_file(path)

        # 2. 切分（多文档 → 多 chunks）
        all_chunks: list[tuple[Document, SplitChunk]] = []
        for doc in loaded_docs:
            chunks = self._splitter.split_document(doc)
            for chunk in chunks:
                all_chunks.append((doc, chunk))

        if not all_chunks:
            raise RagError(f"文件切分结果为空: {source_path}")

        # 3. 检查已存在
        existing = store.get(where={"source_path": source_path})
        if existing["ids"] and not reindex:
            return self._make_doc_info(
                source_path, loaded_docs[0], len(existing["ids"])
            )
        if existing["ids"]:
            store.delete(ids=existing["ids"])

        # 4. 构建 LangChain Document 列表
        content_hash = _sha256("".join(d.page_content for d in loaded_docs))
        ids: list[str] = []
        documents: list[Document] = []
        for doc, chunk in all_chunks:
            chunk_id = f"{content_hash}#{chunk.index}"
            ids.append(chunk_id)
            metadata = {
                **doc.metadata,
                "source_path": source_path,
                "chunk_index": chunk.index,
                "content_hash": content_hash,
                **chunk.metadata,
            }
            documents.append(Document(page_content=chunk.content, metadata=metadata))

        # 5. 写入 Chroma（自动调用 embeddings.embed_documents）
        store.add_documents(documents=documents, ids=ids)

        return self._make_doc_info(source_path, loaded_docs[0], len(all_chunks))

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

        # Chroma 自动调用 embeddings.embed_query
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

    def delete_file(
        self,
        path: str | Path,
        *,
        session_id: str | None = None,
    ) -> bool:
        """删除文件的所有 chunk。"""
        source_path = str(Path(path).resolve())
        store = self._get_store(session_id)
        existing = store.get(where={"source_path": source_path})
        if not existing["ids"]:
            return False
        store.delete(ids=existing["ids"])
        return True

    def delete_all(self, *, session_id: str | None = None) -> int:
        """清空指定 collection 的所有数据。"""
        store = self._get_store(session_id)
        all_data = store.get()
        count = len(all_data["ids"]) if all_data["ids"] else 0
        if count > 0:
            store.delete(ids=all_data["ids"])
        return count

    # ── 会话管理 ──────────────────────────────────────────

    def list_sessions(self) -> list[str]:
        """列出所有会话级知识库的 session_id。"""
        store = self._get_store()
        client = store._client
        prefix = f"{self._base_collection}_"
        sessions: list[str] = []
        for name in client.list_collections():
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
            store._client.delete_collection(collection_name)
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
    ) -> list[RagDocumentInfo]:
        """列出所有已索引文件（按 source_path 去重）。"""
        store = self._get_store(session_id)
        all_data = store.get()
        if not all_data["ids"]:
            return []

        seen: dict[str, RagDocumentInfo] = {}
        for meta in all_data["metadatas"]:
            sp = meta.get("source_path", "")
            if sp and sp not in seen:
                seen[sp] = RagDocumentInfo(
                    source_path=sp,
                    title=meta.get("title", ""),
                    chunk_count=0,
                    mime_type=meta.get("mime_type", ""),
                )
            if sp in seen:
                seen[sp] = RagDocumentInfo(
                    source_path=sp,
                    title=seen[sp].title,
                    chunk_count=seen[sp].chunk_count + 1,
                    mime_type=seen[sp].mime_type,
                )
        return list(seen.values())

    def get_stats(self, *, session_id: str | None = None) -> dict:
        """返回向量库统计信息。"""
        store = self._get_store(session_id)
        all_data = store.get()
        total = len(all_data["ids"]) if all_data["ids"] else 0
        return {
            "total_chunks": total,
            "collection_name": store._collection.name,
        }

    # ── 内部 ──────────────────────────────────────────────

    def _get_settings(self):
        """获取配置。"""
        return self._settings

    @staticmethod
    def _make_doc_info(
        source_path: str,
        doc: Document,
        chunk_count: int,
    ) -> RagDocumentInfo:
        """从加载结果构建文件摘要。"""
        meta = doc.metadata if doc.metadata else {}
        return RagDocumentInfo(
            source_path=source_path,
            title=meta.get("title", ""),
            chunk_count=chunk_count,
            mime_type=meta.get("mime_type", ""),
        )


def _sha256(text: str) -> str:
    """计算文本 SHA-256 哈希。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_rag_service(
    *,
    embeddings: Embeddings,
    loader: LoaderStrategy,
    splitter: SplitterStrategy,
    settings: object,
    prompt_service: object,
) -> RagService:
    """工厂函数：创建 RagService。

    所有依赖必须由调用方（DI 容器）显式传入。

    Args:
        embeddings: Embeddings 实例。
        loader: 文档加载器。
        splitter: 文本切割器。
        settings: 全局配置。
        prompt_service: 提示词服务。

    Returns:
        配置好的 RagService 实例。
    """
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
