"""RAG 索引和检索服务。"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

from src.ai.storage.database import get_session
from src.ai.utils.token_utils import token_counter

from .embeddings import RagEmbeddingService
from .loaders import FileDocumentLoader
from src.ai.storage.rag_models import RagDocument, RagEmbedding
from src.ai.storage.rag_repository import (
    RagChunkRepository,
    RagDocumentRepository,
    RagEmbeddingRepository,
    delete_document_tree,
)
from .splitters import RagTextSplitter


@dataclass(frozen=True)
class RagSearchResult:
    document_id: int
    chunk_id: int
    source_path: str
    title: str | None
    content: str
    score: float


class RagService:
    """文件索引、向量存储和相似度检索。"""

    def __init__(
        self,
        *,
        loader: FileDocumentLoader | None = None,
        splitter: RagTextSplitter | None = None,
        embeddings: RagEmbeddingService | None = None,
    ) -> None:
        self._loader = loader or FileDocumentLoader()
        self._splitter = splitter or RagTextSplitter()
        self._embeddings = embeddings or RagEmbeddingService()

    def index_file(
        self,
        path: str | Path,
        *,
        embedding_model_id: int | None = None,
        provider_key: str | None = None,
        model_key: str | None = None,
        reindex: bool = False,
    ) -> RagDocument:
        loaded = self._loader.load(path)
        content_hash = _sha256(loaded.content)
        chunks = self._splitter.split(loaded.content)
        vectors = self._embeddings.embed_texts(
            [chunk.content for chunk in chunks],
            model_id=embedding_model_id,
            provider_key=provider_key,
            model_key=model_key,
        )

        with get_session() as session:
            doc_repo = RagDocumentRepository(session)
            existing = doc_repo.get_by_source_hash(loaded.source_path, content_hash)
            if existing is not None and not reindex:
                return existing
            if existing is not None and existing.id is not None:
                delete_document_tree(session, existing.id)

            document = doc_repo.create(
                source_path=loaded.source_path,
                title=loaded.title,
                content_hash=content_hash,
                mime_type=loaded.mime_type,
                size_bytes=loaded.size_bytes,
                chunk_count=len(chunks),
            )
            chunk_repo = RagChunkRepository(session)
            embedding_repo = RagEmbeddingRepository(session)
            for chunk, vector in zip(chunks, vectors.vectors, strict=False):
                db_chunk = chunk_repo.create(
                    document_id=document.id,
                    chunk_index=chunk.index,
                    content=chunk.content,
                    content_hash=_sha256(chunk.content),
                    token_count=token_counter.count_text_tokens(chunk.content),
                )
                embedding = RagEmbedding(
                    chunk_id=db_chunk.id,
                    embedding_model=vectors.model_name,
                    dimension=len(vector),
                    vector="[]",
                )
                embedding.set_vector(vector)
                embedding_repo.save(embedding)
            return document

    def index_directory(
        self,
        path: str | Path,
        *,
        patterns: list[str] | None = None,
        reindex: bool = False,
    ) -> list[RagDocument]:
        root = Path(path)
        patterns = patterns or ["**/*.md", "**/*.txt", "**/*.py", "**/*.json", "**/*.yaml", "**/*.yml"]
        documents: list[RagDocument] = []
        for pattern in patterns:
            for file_path in root.glob(pattern):
                if file_path.is_file():
                    documents.append(self.index_file(file_path, reindex=reindex))
        return documents

    def search(self, query: str, *, top_k: int = 5, embedding_model: str | None = None) -> list[RagSearchResult]:
        query_result = self._embeddings.embed_texts([query])
        query_vector = query_result.vectors[0]
        with get_session() as session:
            embedding_repo = RagEmbeddingRepository(session)
            chunk_repo = RagChunkRepository(session)
            doc_repo = RagDocumentRepository(session)
            results: list[RagSearchResult] = []
            for embedding in embedding_repo.list_by_model(embedding_model, limit=10000):
                chunk = chunk_repo.get_by_id(embedding.chunk_id)
                if chunk is None:
                    continue
                document = doc_repo.get_by_id(chunk.document_id)
                if document is None or document.id is None or chunk.id is None:
                    continue
                score = cosine_similarity(query_vector, embedding.get_vector())
                results.append(
                    RagSearchResult(
                        document_id=document.id,
                        chunk_id=chunk.id,
                        source_path=document.source_path,
                        title=document.title,
                        content=chunk.content,
                        score=score,
                    )
                )
        return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]

    def build_context(self, query: str, *, top_k: int = 5) -> str:
        results = self.search(query, top_k=top_k)
        return "\n\n".join(
            f"[{index}] {result.title or result.source_path}\n{result.content}"
            for index, result in enumerate(results, start=1)
        )


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    dot = sum(left[index] * right[index] for index in range(size))
    left_norm = math.sqrt(sum(value * value for value in left[:size]))
    right_norm = math.sqrt(sum(value * value for value in right[:size]))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


rag_service = RagService()
