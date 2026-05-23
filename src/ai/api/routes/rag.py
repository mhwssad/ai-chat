"""RAG 路由。"""

from __future__ import annotations

from fastapi import APIRouter

from src.ai.api.schemas.rag import (
    RagDocumentResponse,
    RagIndexDirectoryRequest,
    RagIndexFileRequest,
    RagSearchRequest,
    RagSearchResultResponse,
)
from src.ai.api.services.rag_service import RagApiService

router = APIRouter()


@router.post("/index-file", response_model=RagDocumentResponse)
async def index_file(payload: RagIndexFileRequest):
    document = RagApiService().index_file(
        path=payload.path,
        embedding_model_id=payload.embedding_model_id,
        provider_key=payload.provider_key,
        model_key=payload.model_key,
        reindex=payload.reindex,
    )
    return _document_response(document)


@router.post("/index-directory", response_model=list[RagDocumentResponse])
async def index_directory(payload: RagIndexDirectoryRequest):
    documents = RagApiService().index_directory(
        path=payload.path,
        patterns=payload.patterns,
        reindex=payload.reindex,
    )
    return [_document_response(document) for document in documents]


@router.post("/search", response_model=list[RagSearchResultResponse])
async def search(payload: RagSearchRequest):
    results = RagApiService().search(payload.query, top_k=payload.top_k)
    return [RagSearchResultResponse(**result.__dict__) for result in results]


@router.post("/context")
async def build_context(payload: RagSearchRequest):
    return {"context": RagApiService().build_context(payload.query, top_k=payload.top_k)}


def _document_response(document) -> RagDocumentResponse:
    return RagDocumentResponse(
        id=document.id,
        source_path=document.source_path,
        title=document.title,
        chunk_count=document.chunk_count,
        status=document.status,
    )

