"""RAG 数据库模型。"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import Column, Index, String, UniqueConstraint
from sqlmodel import Field, SQLModel


def _dt_now() -> datetime:
    return datetime.now()


class RagDocument(SQLModel, table=True):
    """被索引的文档。"""

    __tablename__ = "rag_documents"
    __table_args__ = (
        UniqueConstraint("source_path", "content_hash", name="uq_rag_document_source_hash"),
        Index("idx_rag_documents_source_path", "source_path"),
    )

    id: int | None = Field(default=None, primary_key=True)
    source_path: str
    source_type: str = Field(default="file")
    title: str | None = None
    content_hash: str
    mime_type: str | None = None
    size_bytes: int | None = None
    chunk_count: int = Field(default=0)
    status: str = Field(default="indexed")
    created_at: datetime = Field(default_factory=_dt_now)
    updated_at: datetime = Field(default_factory=_dt_now)
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
    )


class RagChunk(SQLModel, table=True):
    """文档切分后的 chunk。"""

    __tablename__ = "rag_chunks"
    __table_args__ = (Index("idx_rag_chunks_document", "document_id", "chunk_index"),)

    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="rag_documents.id")
    chunk_index: int
    content: str
    content_hash: str
    token_count: int | None = None
    created_at: datetime = Field(default_factory=_dt_now)
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
    )


class RagEmbedding(SQLModel, table=True):
    """chunk 对应的向量。"""

    __tablename__ = "rag_embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", "embedding_model", name="uq_rag_embedding_chunk_model"),
        Index("idx_rag_embeddings_model", "embedding_model"),
    )

    id: int | None = Field(default=None, primary_key=True)
    chunk_id: int = Field(foreign_key="rag_chunks.id")
    embedding_model: str
    dimension: int
    vector: str
    created_at: datetime = Field(default_factory=_dt_now)
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
    )

    def get_vector(self) -> list[float]:
        try:
            data = json.loads(self.vector)
        except json.JSONDecodeError:
            return []
        return [float(item) for item in data]

    def set_vector(self, vector: list[float]) -> None:
        self.vector = json.dumps(vector, ensure_ascii=False)

