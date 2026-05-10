"""FAISS 向量存储后端。"""

from typing import Optional

from ..factory import register_vectorstore
from ..models import VectorStoreConfig, VectorStoreProvider


class _EmbeddingAdapter:
    """将 llm_factory.embed_batch 适配为 LangChain Embeddings 接口。"""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        from src.ai_chat.llm import llm_factory
        return llm_factory.embed_batch(texts, self._model_name)

    def embed_query(self, text: str) -> list[float]:
        from src.ai_chat.llm import llm_factory
        return llm_factory.embed(text, self._model_name)


@register_vectorstore("faiss", lambda: VectorStoreConfig())
class FAISSStore(VectorStoreProvider):
    """基于 langchain-community FAISS 集成的向量存储。"""

    def __init__(self, config: Optional[VectorStoreConfig] = None) -> None:
        self._config = config or VectorStoreConfig()
        self._embedding = _EmbeddingAdapter(self._config.embedding_model)
        self._store = None

    def _get_or_create_store(self):
        if self._store is None:
            from langchain_community.vectorstores import FAISS
            self._store = FAISS.from_texts(
                ["__init__"],
                self._embedding,
                metadatas=[{"__init": True}],
            )
        return self._store

    def add_texts(
        self, texts: list[str], metadatas: Optional[list[dict]] = None
    ) -> None:
        from langchain_community.vectorstores import FAISS

        if self._store is None:
            metadatas = metadatas or [{} for _ in texts]
            self._store = FAISS.from_texts(texts, self._embedding, metadatas=metadatas)
        else:
            self._store.add_texts(texts, metadatas=metadatas)

    def similarity_search(self, query: str, k: int = 4) -> list[dict]:
        store = self._get_or_create_store()
        docs = store.similarity_search(query, k=k)
        return [
            {"content": doc.page_content, "metadata": doc.metadata}
            for doc in docs
            if not doc.metadata.get("__init")
        ]

    def save(self, path: str) -> None:
        store = self._get_or_create_store()
        store.save_local(path)

    def load(self, path: str) -> None:
        from langchain_community.vectorstores import FAISS
        self._store = FAISS.load_local(
            path, self._embedding, allow_dangerous_deserialization=True
        )
