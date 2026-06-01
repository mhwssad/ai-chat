"""RAG 路由。"""

from fastapi import APIRouter, UploadFile, File, Form

from src.ai.api.deps import RagServiceDep
from src.ai.api.schemas.common import MessageResponse
from src.ai.api.schemas.rag import (
    RagBatchDeleteRequest,
    RagBatchDeleteResponse,
    RagChunkResponse,
    RagDocumentDetailResponse,
    RagDocumentInfoResponse,
    RagGlobalStatsResponse,
    RagIndexRequest,
    RagSearchRequest,
    RagSearchResultResponse,
    RagSessionInfo,
    RagStatsResponse,
    RagTextIndexRequest,
    RagUpdateTextRequest,
    RagUrlIndexRequest,
)

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/index", response_model=list[RagDocumentInfoResponse])
async def index_documents(
    request: RagIndexRequest,
    service: RagServiceDep,
):
    """索引文档。

    索引单个文件或目录中的所有文件。

    Args:
        request: 索引请求。
    """
    from pathlib import Path

    path = Path(request.path)

    if path.is_dir():
        documents = service.index_directory(
            path,
            session_id=request.session_id,
            patterns=request.patterns,
            reindex=request.reindex,
        )
    else:
        doc = service.index_file(
            path,
            session_id=request.session_id,
            reindex=request.reindex,
        )
        documents = [doc]

    return [
        RagDocumentInfoResponse(
            source_path=d.source_path,
            title=d.title,
            chunk_count=d.chunk_count,
            mime_type=d.mime_type,
        )
        for d in documents
    ]


@router.post("/upload", response_model=RagDocumentInfoResponse)
async def upload_file(
    service: RagServiceDep,
    file: UploadFile = File(description="上传的文件"),
    session_id: str | None = Form(default=None, description="会话 ID"),
    reindex: bool = Form(default=False, description="是否重新索引"),
):
    """上传文件并索引。

    Args:
        file: 上传的文件。
        session_id: 会话 ID。
        reindex: 是否重新索引。
    """
    data = await file.read()
    doc = service.index_stream(
        data,
        mime_type=file.content_type,
        filename=file.filename,
        session_id=session_id,
        reindex=reindex,
    )
    return RagDocumentInfoResponse(
        source_path=doc.source_path,
        title=doc.title,
        chunk_count=doc.chunk_count,
        mime_type=doc.mime_type,
    )


@router.post("/url", response_model=RagDocumentInfoResponse)
async def index_from_url(
    request: RagUrlIndexRequest,
    service: RagServiceDep,
):
    """从 URL 下载并索引文档。

    Args:
        request: URL 索引请求。
    """
    doc = service.index_url(
        request.url,
        session_id=request.session_id,
        reindex=request.reindex,
    )
    return RagDocumentInfoResponse(
        source_path=doc.source_path,
        title=doc.title,
        chunk_count=doc.chunk_count,
        mime_type=doc.mime_type,
    )


@router.post("/text", response_model=RagDocumentInfoResponse)
async def index_from_text(
    request: RagTextIndexRequest,
    service: RagServiceDep,
):
    """索引原始文本。

    Args:
        request: 文本索引请求。
    """
    doc = service.index_text(
        request.text,
        title=request.title,
        session_id=request.session_id,
        reindex=request.reindex,
    )
    return RagDocumentInfoResponse(
        source_path=doc.source_path,
        title=doc.title,
        chunk_count=doc.chunk_count,
        mime_type=doc.mime_type,
    )


@router.post("/search", response_model=list[RagSearchResultResponse])
async def search_documents(
    request: RagSearchRequest,
    service: RagServiceDep,
):
    """向量搜索。

    Args:
        request: 搜索请求。
    """
    results = service.search(
        request.query,
        session_id=request.session_id,
        top_k=request.top_k,
    )

    return [
        RagSearchResultResponse(
            id=r.id,
            source_path=r.source_path,
            title=r.title,
            content=r.content,
            chunk_index=r.chunk_index,
            score=r.score,
        )
        for r in results
    ]


@router.get("/documents", response_model=list[RagDocumentInfoResponse])
async def list_documents(
    service: RagServiceDep,
    session_id: str | None = None,
):
    """列出已索引文档。

    Args:
        session_id: 会话 ID。
    """
    documents = service.list_documents(session_id=session_id)

    return [
        RagDocumentInfoResponse(
            source_path=d.source_path,
            title=d.title,
            chunk_count=d.chunk_count,
            mime_type=d.mime_type,
        )
        for d in documents
    ]


@router.put("/text", response_model=RagDocumentInfoResponse)
async def update_text_index(
    request: RagUpdateTextRequest,
    service: RagServiceDep,
):
    """更新已索引文本内容（先删后建）。

    Args:
        request: 更新文本请求。
    """
    doc = service.update_text(
        request.text,
        source_path=request.source_path,
        title=request.title,
        session_id=request.session_id,
    )
    return RagDocumentInfoResponse(
        source_path=doc.source_path,
        title=doc.title,
        chunk_count=doc.chunk_count,
        mime_type=doc.mime_type,
    )


@router.post("/hybrid-search", response_model=list[RagSearchResultResponse])
async def hybrid_search(
    request: RagSearchRequest,
    service: RagServiceDep,
):
    """混合搜索（向量 + BM25）。

    Args:
        request: 搜索请求。
    """
    results = service.hybrid_search(
        request.query,
        session_id=request.session_id,
        top_k=request.top_k,
    )
    return [
        RagSearchResultResponse(
            id=r.id,
            source_path=r.source_path,
            title=r.title,
            content=r.content,
            chunk_index=r.chunk_index,
            score=r.score,
        )
        for r in results
    ]


@router.post("/context")
async def build_rag_context(
    request: RagSearchRequest,
    service: RagServiceDep,
):
    """构建 RAG 上下文文本。

    Args:
        request: 搜索请求（使用 query、session_id、top_k）。
    """
    context = service.build_context(
        request.query,
        session_id=request.session_id,
        top_k=request.top_k,
    )
    return {"context": context}


@router.get(
    "/documents/{path:path}/chunks",
    response_model=RagDocumentDetailResponse,
)
async def get_document_chunks(
    path: str,
    service: RagServiceDep,
    session_id: str | None = None,
):
    """获取文档的所有 chunks 详情。

    Args:
        path: 文档 source_path。
        session_id: 会话 ID。
    """
    chunks = service.get_document_chunks(path, session_id=session_id)
    if not chunks:
        from src.ai.exception.rag_exception import RagError

        raise RagError(f"文档不存在: {path}", context={"path": path})

    docs = service.list_documents(session_id=session_id)
    doc_info = next((d for d in docs if d.source_path == path), None)

    return RagDocumentDetailResponse(
        source_path=path,
        title=doc_info.title if doc_info else "",
        chunk_count=len(chunks),
        mime_type=doc_info.mime_type if doc_info else "",
        chunks=[
            RagChunkResponse(
                id=c["id"],
                content=c["content"],
                chunk_index=c["chunk_index"],
                metadata=c["metadata"],
            )
            for c in chunks
        ],
    )


@router.post("/documents/batch-delete", response_model=RagBatchDeleteResponse)
async def batch_delete_documents(
    request: RagBatchDeleteRequest,
    service: RagServiceDep,
):
    """批量删除多个文档。

    Args:
        request: 批量删除请求。
    """
    results = service.delete_documents_batch(
        request.paths, session_id=request.session_id
    )
    success_count = sum(1 for v in results.values() if v)
    fail_count = sum(1 for v in results.values() if not v)
    return RagBatchDeleteResponse(
        results=results,
        success_count=success_count,
        fail_count=fail_count,
    )


@router.delete("/documents", response_model=MessageResponse)
async def delete_document(
    service: RagServiceDep,
    path: str,
    session_id: str | None = None,
):
    """删除文档。

    Args:
        path: 文件路径。
        session_id: 会话 ID。
    """
    success = service.delete_file(path, session_id=session_id)
    if not success:
        from src.ai.exception.rag_exception import RagError

        raise RagError(f"文档不存在: {path}", context={"path": path})

    return MessageResponse(message=f"文档 {path} 已删除")


@router.delete("/all", response_model=MessageResponse)
async def clear_knowledge_base(
    service: RagServiceDep,
    session_id: str | None = None,
):
    """清空知识库。

    Args:
        session_id: 会话 ID。
    """
    count = service.delete_all(session_id=session_id)
    return MessageResponse(message=f"已删除 {count} 个分块")


@router.get("/stats", response_model=RagStatsResponse)
async def get_rag_stats(
    service: RagServiceDep,
    session_id: str | None = None,
):
    """获取 RAG 统计。

    Args:
        session_id: 会话 ID。
    """
    stats = service.get_stats(session_id=session_id)

    return RagStatsResponse(
        total_chunks=stats.get("total_chunks", 0),
        collection_name=stats.get("collection_name", ""),
    )


@router.get("/sessions", response_model=list[RagSessionInfo])
async def list_rag_sessions(
    service: RagServiceDep,
):
    """列出所有 RAG 会话。"""
    sessions = service.list_sessions()
    result: list[RagSessionInfo] = []
    for session_id in sessions:
        stats = service.get_stats(session_id=session_id)
        docs = service.list_documents(session_id=session_id)
        result.append(
            RagSessionInfo(
                session_id=session_id,
                document_count=len(docs),
                total_chunks=stats.get("total_chunks", 0),
            )
        )
    return result


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def delete_rag_session(
    session_id: str,
    service: RagServiceDep,
):
    """删除会话及其知识库。

    Args:
        session_id: 会话 ID。
    """
    success = service.delete_session(session_id)
    if not success:
        from src.ai.exception.rag_exception import RagError

        raise RagError(
            f"会话不存在或删除失败: {session_id}",
            context={"session_id": session_id},
        )
    return MessageResponse(message=f"会话 {session_id} 已删除")


@router.get("/sessions/{session_id}/stats", response_model=RagStatsResponse)
async def get_session_stats(
    session_id: str,
    service: RagServiceDep,
):
    """获取会话统计。

    Args:
        session_id: 会话 ID。
    """
    stats = service.get_stats(session_id=session_id)
    return RagStatsResponse(
        total_chunks=stats.get("total_chunks", 0),
        collection_name=stats.get("collection_name", ""),
    )


@router.get("/global-stats", response_model=RagGlobalStatsResponse)
async def get_global_stats(
    service: RagServiceDep,
):
    """获取全局统计（跨所有会话）。"""
    stats = service.get_all_stats()
    return RagGlobalStatsResponse(
        default_chunks=stats["default_chunks"],
        sessions=[
            RagSessionInfo(
                session_id=s["session_id"],
                document_count=s["document_count"],
                total_chunks=s["total_chunks"],
            )
            for s in stats["sessions"]
        ],
        total_sessions=stats["total_sessions"],
        total_chunks=stats["total_chunks"],
    )
