"""FAISS 向量存储后端。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.ai_chat.config.logging_setup import get_logger

from ..factory import register_vectorstore
from ..models import VectorStoreConfig, VectorStoreProvider

logger = get_logger(__name__)

# FAISS 属于 heavy dependency，延迟导入并缓存到模块变量
_FAISS = None


def _get_faiss():
    """延迟导入 FAISS 并缓存。"""
    global _FAISS
    if _FAISS is None:
        from langchain_community.vectorstores import FAISS as _F

        _FAISS = _F
    return _FAISS


# llm_factory 轻量但存在循环导入风险，延迟导入并缓存
_llm_factory = None


def _get_llm_factory():
    global _llm_factory
    if _llm_factory is None:
        from src.ai_chat.llm import llm_factory as _lf

        _llm_factory = _lf
    return _llm_factory


_INIT_MARKER = "__faiss_init_marker"


class _EmbeddingAdapter:
    """将 llm_factory.embed_batch 适配为 LangChain Embeddings 接口。"""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return _get_llm_factory().embed_batch(texts, self._model_name)

    def embed_query(self, text: str) -> list[float]:
        return _get_llm_factory().embed(text, self._model_name)


@register_vectorstore("faiss", lambda: VectorStoreConfig())
class FAISSStore(VectorStoreProvider):
    """基于 langchain-community FAISS 集成的向量存储。"""

    def __init__(self, config: Optional[VectorStoreConfig] = None) -> None:
        self._config = config or VectorStoreConfig()
        self._embedding = _EmbeddingAdapter(self._config.embedding_model)
        self._store = None

    def _get_or_create_store(self):
        if self._store is None:
            # 尝试从持久化路径自动加载
            if self._config.persist_path:
                persist = Path(self._config.persist_path)
                if persist.exists() and any(persist.iterdir()):
                    try:
                        FAISS = _get_faiss()
                        self._store = FAISS.load_local(
                            str(persist),
                            self._embedding,
                            allow_dangerous_deserialization=True,
                        )
                        logger.info("FAISS 索引自动加载: %s", persist)
                        return self._store
                    except Exception as e:
                        logger.warning("FAISS 自动加载失败，将创建新索引: %s", e)

            FAISS = _get_faiss()
            self._store = FAISS.from_texts(
                ["__init__"],
                self._embedding,
                metadatas=[{_INIT_MARKER: True}],
            )
        return self._store

    def add_texts(
        self, texts: list[str], metadatas: Optional[list[dict]] = None
    ) -> None:
        # 跳过空文本
        valid = [(t, m) for t, m in zip(texts, metadatas or [{}] * len(texts)) if t.strip()]
        if not valid:
            return
        clean_texts, clean_metas = zip(*valid)

        if self._store is None:
            FAISS = _get_faiss()
            self._store = FAISS.from_texts(list(clean_texts), self._embedding, metadatas=list(clean_metas))
        else:
            self._store.add_texts(list(clean_texts), metadatas=list(clean_metas))

    def similarity_search(self, query: str, k: int = 4) -> list[dict]:
        store = self._get_or_create_store()
        docs = store.similarity_search(query, k=k)
        return [
            {"content": doc.page_content, "metadata": doc.metadata}
            for doc in docs
            if not doc.metadata.get(_INIT_MARKER)
        ]

    def batch_similarity_search(self, queries: list[str], k: int = 4) -> list[list[dict]]:
        """批量相似度搜索，复用 embedding 计算提高效率。"""
        results = []
        for query in queries:
            results.append(self.similarity_search(query, k=k))
        return results

    def delete_texts(self, ids: list[str]) -> int:
        """FAISS 不支持按 ID 删除，返回 0。"""
        return 0

    def save(self, path: str) -> None:
        store = self._get_or_create_store()
        store.save_local(path)

    def load(self, path: str) -> None:
        FAISS = _get_faiss()
        self._store = FAISS.load_local(
            path, self._embedding, allow_dangerous_deserialization=True
        )
