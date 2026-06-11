"""RAG 管理路由 — 文档索引、搜索、管理。"""

from __future__ import annotations

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query

from src.ai.api.schemas.common import MessageResponse
from src.ai.api.schemas.rag import (
    RagDeleteAllResponse,
    RagDocumentInfoResponse,
    RagIndexDirectoryRequest,
    RagIndexFileRequest,
    RagIndexTextRequest,
    RagIndexUrlRequest,
    RagSearchRequest,
    RagSearchResultResponse,
    RagStatsResponse,
)
from src.ai.core.container import AppContainer
from src.ai.service.rag_service import RagApiService

router = APIRouter()


@router.post("/index/file", response_model=RagDocumentInfoResponse, summary="索引文件")
@inject
async def index_file(
    req: RagIndexFileRequest,
    svc: Annotated[
        RagApiService, Depends(Provide[AppContainer.service_container.rag_api_service])
    ],
) -> RagDocumentInfoResponse:
    """将文件内容索引到向量库。"""
    result = await svc.index_file(
        req.path, session_id=req.session_id, reindex=req.reindex
    )
    return RagDocumentInfoResponse(**result)


@router.post("/index/url", response_model=RagDocumentInfoResponse, summary="索引 URL")
@inject
async def index_url(
    req: RagIndexUrlRequest,
    svc: Annotated[
        RagApiService, Depends(Provide[AppContainer.service_container.rag_api_service])
    ],
) -> RagDocumentInfoResponse:
    """将 URL 内容索引到向量库。"""
    result = await svc.index_url(
        req.url, session_id=req.session_id, reindex=req.reindex
    )
    return RagDocumentInfoResponse(**result)


@router.post("/index/text", response_model=RagDocumentInfoResponse, summary="索引文本")
@inject
async def index_text(
    req: RagIndexTextRequest,
    svc: Annotated[
        RagApiService, Depends(Provide[AppContainer.service_container.rag_api_service])
    ],
) -> RagDocumentInfoResponse:
    """将文本内容索引到向量库。"""
    result = await svc.index_text(
        req.text, title=req.title, session_id=req.session_id, reindex=req.reindex
    )
    return RagDocumentInfoResponse(**result)


@router.post(
    "/index/directory", response_model=list[RagDocumentInfoResponse], summary="索引目录"
)
@inject
async def index_directory(
    req: RagIndexDirectoryRequest,
    svc: Annotated[
        RagApiService, Depends(Provide[AppContainer.service_container.rag_api_service])
    ],
) -> list[RagDocumentInfoResponse]:
    """将目录下的文件批量索引到向量库。"""
    results = await svc.index_directory(
        req.path, patterns=req.patterns, session_id=req.session_id, reindex=req.reindex
    )
    return [RagDocumentInfoResponse(**r) for r in results]


@router.post(
    "/search", response_model=list[RagSearchResultResponse], summary="向量搜索"
)
@inject
async def search(
    req: RagSearchRequest,
    svc: Annotated[
        RagApiService, Depends(Provide[AppContainer.service_container.rag_api_service])
    ],
) -> list[RagSearchResultResponse]:
    """向量相似度搜索。"""
    results = await svc.search(req.query, session_id=req.session_id, top_k=req.top_k)
    return [RagSearchResultResponse(**r) for r in results]


@router.post(
    "/search/hybrid", response_model=list[RagSearchResultResponse], summary="混合搜索"
)
@inject
async def hybrid_search(
    req: RagSearchRequest,
    svc: Annotated[
        RagApiService, Depends(Provide[AppContainer.service_container.rag_api_service])
    ],
) -> list[RagSearchResultResponse]:
    """混合搜索（向量 + BM25）。"""
    results = await svc.hybrid_search(
        req.query, session_id=req.session_id, top_k=req.top_k
    )
    return [RagSearchResultResponse(**r) for r in results]


@router.get(
    "/documents", response_model=list[RagDocumentInfoResponse], summary="列出文档"
)
@inject
async def list_documents(
    svc: Annotated[
        RagApiService, Depends(Provide[AppContainer.service_container.rag_api_service])
    ],
    session_id: str | None = Query(default=None, description="按会话 ID 过滤"),
    status: str | None = Query(default="active", description="按状态过滤"),
) -> list[RagDocumentInfoResponse]:
    """列出已索引的文档。"""
    docs = await svc.list_documents(session_id=session_id, status=status)
    return [RagDocumentInfoResponse(**d) for d in docs]


@router.delete(
    "/documents/{path:path}", response_model=MessageResponse, summary="删除文档"
)
@inject
async def delete_file(
    path: str,
    svc: Annotated[
        RagApiService, Depends(Provide[AppContainer.service_container.rag_api_service])
    ],
    session_id: str | None = Query(default=None, description="会话 ID"),
) -> MessageResponse:
    """删除指定文档的索引。"""
    deleted = await svc.delete_file(path, session_id=session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"文档不存在: {path}")
    return MessageResponse(message=f"已删除: {path}")


@router.post(
    "/documents/delete-all", response_model=RagDeleteAllResponse, summary="删除全部文档"
)
@inject
async def delete_all(
    svc: Annotated[
        RagApiService, Depends(Provide[AppContainer.service_container.rag_api_service])
    ],
    session_id: str | None = Query(default=None, description="会话 ID"),
) -> RagDeleteAllResponse:
    """删除全部文档索引。"""
    count = await svc.delete_all(session_id=session_id)
    return RagDeleteAllResponse(deleted_count=count)


@router.get("/stats", response_model=RagStatsResponse, summary="RAG 统计")
@inject
async def get_stats(
    svc: Annotated[
        RagApiService, Depends(Provide[AppContainer.service_container.rag_api_service])
    ],
    session_id: str | None = Query(default=None, description="会话 ID"),
) -> RagStatsResponse:
    """获取 RAG 统计信息。"""
    stats = await svc.get_stats(session_id=session_id)
    return RagStatsResponse(**stats)
