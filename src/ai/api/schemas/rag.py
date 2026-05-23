"""RAG API schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RagIndexFileRequest(BaseModel):
    path: str
    embedding_model_id: int | None = None
    provider_key: str | None = None
    model_key: str | None = None
    reindex: bool = False


class RagIndexDirectoryRequest(BaseModel):
    path: str
    patterns: list[str] | None = None
    reindex: bool = False


class RagDocumentResponse(BaseModel):
    id: int | None
    source_path: str
    title: str | None
    chunk_count: int
    status: str


class RagSearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)


class RagSearchResultResponse(BaseModel):
    document_id: int
    chunk_id: int
    source_path: str
    title: str | None
    content: str
    score: float

