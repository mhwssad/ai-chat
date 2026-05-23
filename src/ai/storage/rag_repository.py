"""RAG 数据仓库。"""

from __future__ import annotations

from sqlmodel import Session, select

from src.ai.storage.base_repository import BaseRepository
from src.ai.storage.rag_models import RagChunk, RagDocument, RagEmbedding


class RagDocumentRepository(BaseRepository[RagDocument]):
    """RAG 文档仓库。"""

    model = RagDocument

    def get_by_source_hash(self, source_path: str, content_hash: str) -> RagDocument | None:
        stmt = select(RagDocument).where(
            RagDocument.source_path == source_path,
            RagDocument.content_hash == content_hash,
        )
        return self.session.exec(stmt).first()


class RagChunkRepository(BaseRepository[RagChunk]):
    """RAG chunk 仓库。"""

    model = RagChunk

    def get_by_document(self, document_id: int) -> list[RagChunk]:
        return self.list(document_id=document_id, order_by="chunk_index", descending=False)


class RagEmbeddingRepository(BaseRepository[RagEmbedding]):
    """RAG embedding 仓库。"""

    model = RagEmbedding

    def list_by_model(self, embedding_model: str | None = None, *, limit: int = 10000) -> list[RagEmbedding]:
        if embedding_model:
            return self.list(embedding_model=embedding_model, limit=limit)
        return self.list(limit=limit)


def delete_document_tree(session: Session, document_id: int) -> None:
    """删除文档及其 chunk/embedding。"""
    chunk_repo = RagChunkRepository(session)
    embedding_repo = RagEmbeddingRepository(session)
    doc_repo = RagDocumentRepository(session)
    for chunk in chunk_repo.get_by_document(document_id):
        for embedding in embedding_repo.list(chunk_id=chunk.id):
            embedding_repo.delete(embedding)
        chunk_repo.delete(chunk)
    document = doc_repo.get_by_id(document_id)
    if document is not None:
        doc_repo.delete(document)

