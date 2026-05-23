"""RAG API 服务。"""

from __future__ import annotations

from src.ai.rag import rag_service


class RagApiService:
    def index_file(self, **kwargs):
        return rag_service.index_file(**kwargs)

    def index_directory(self, **kwargs):
        return rag_service.index_directory(**kwargs)

    def search(self, query: str, *, top_k: int = 5):
        return rag_service.search(query, top_k=top_k)

    def build_context(self, query: str, *, top_k: int = 5) -> str:
        return rag_service.build_context(query, top_k=top_k)

