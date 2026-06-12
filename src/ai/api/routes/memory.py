"""记忆管理路由 — CRUD、搜索、提取、统计。"""

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query

from src.ai.api.schemas.common import MessageResponse
from src.ai.api.schemas.memory import (
    MemoryEntryResponse,
    MemoryExtractRequest,
    MemorySearchRequest,
    MemorySearchResultResponse,
    MemoryStatsResponse,
    MemoryWriteRequestSchema,
)
from src.ai.core.container import AppContainer
from src.ai.service.memory_service import MemoryApiService

router = APIRouter()


@router.get("", response_model=list[MemoryEntryResponse], summary="列出记忆")
@inject
async def list_entries(
    svc: Annotated[
        MemoryApiService,
        Depends(Provide[AppContainer.service_container.memory_api_service]),
    ],
    memory_type: str | None = Query(default=None, description="按类型过滤"),
    scope: str | None = Query(default=None, description="按作用域过滤"),
    status: str | None = Query(default=None, description="按状态过滤"),
) -> list[MemoryEntryResponse]:
    """列出记忆条目。"""
    entries = await svc.list_entries(
        memory_type=memory_type, scope=scope, status=status
    )
    return [MemoryEntryResponse(**e) for e in entries]


@router.post("", response_model=MemoryEntryResponse, summary="保存记忆")
@inject
async def save_memory(
    req: MemoryWriteRequestSchema,
    svc: Annotated[
        MemoryApiService,
        Depends(Provide[AppContainer.service_container.memory_api_service]),
    ],
) -> MemoryEntryResponse:
    """保存记忆条目。"""
    entry = await svc.save(
        content=req.content,
        memory_type=req.memory_type,
        name=req.name,
        description=req.description,
        scope=req.scope,
        source_type=req.source_type,
        source_id=req.source_id,
    )
    return MemoryEntryResponse(**entry)


@router.get("/stats", response_model=MemoryStatsResponse, summary="记忆统计")
@inject
async def get_stats(
    svc: Annotated[
        MemoryApiService,
        Depends(Provide[AppContainer.service_container.memory_api_service]),
    ],
) -> MemoryStatsResponse:
    """获取记忆统计信息。"""
    stats = await svc.get_stats()
    return MemoryStatsResponse(**stats)


@router.get("/{name}", response_model=MemoryEntryResponse, summary="获取记忆")
@inject
async def get_memory(
    name: str,
    svc: Annotated[
        MemoryApiService,
        Depends(Provide[AppContainer.service_container.memory_api_service]),
    ],
) -> MemoryEntryResponse:
    """获取指定记忆条目。"""
    entry = await svc.get(name)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"记忆不存在: {name}")
    return MemoryEntryResponse(**entry)


@router.delete("/{name}", response_model=MessageResponse, summary="删除记忆")
@inject
async def delete_memory(
    name: str,
    svc: Annotated[
        MemoryApiService,
        Depends(Provide[AppContainer.service_container.memory_api_service]),
    ],
) -> MessageResponse:
    """删除记忆条目。"""
    await svc.delete(name)
    return MessageResponse(message=f"已删除: {name}")


@router.post("/{name}/disable", response_model=MessageResponse, summary="禁用记忆")
@inject
async def disable_memory(
    name: str,
    svc: Annotated[
        MemoryApiService,
        Depends(Provide[AppContainer.service_container.memory_api_service]),
    ],
) -> MessageResponse:
    """禁用记忆条目。"""
    await svc.disable(name)
    return MessageResponse(message=f"已禁用: {name}")


@router.post("/{name}/enable", response_model=MessageResponse, summary="启用记忆")
@inject
async def enable_memory(
    name: str,
    svc: Annotated[
        MemoryApiService,
        Depends(Provide[AppContainer.service_container.memory_api_service]),
    ],
) -> MessageResponse:
    """启用记忆条目。"""
    await svc.enable(name)
    return MessageResponse(message=f"已启用: {name}")


@router.post(
    "/search", response_model=list[MemorySearchResultResponse], summary="搜索记忆"
)
@inject
async def search_memory(
    req: MemorySearchRequest,
    svc: Annotated[
        MemoryApiService,
        Depends(Provide[AppContainer.service_container.memory_api_service]),
    ],
) -> list[MemorySearchResultResponse]:
    """搜索记忆条目。"""
    results = await svc.search(req.query, limit=req.limit)
    return [MemorySearchResultResponse(**r) for r in results]


@router.post("/extract", summary="从对话提取记忆")
@inject
async def extract_memory(
    req: MemoryExtractRequest,
    svc: Annotated[
        MemoryApiService,
        Depends(Provide[AppContainer.service_container.memory_api_service]),
    ],
) -> list[dict]:
    """从对话中提取记忆。"""
    results = await svc.extract_from_conversation(
        user_message=req.user_message,
        assistant_message=req.assistant_message,
    )
    return results


@router.post("/rebuild-index", response_model=MessageResponse, summary="重建索引")
@inject
async def rebuild_index(
    svc: Annotated[
        MemoryApiService,
        Depends(Provide[AppContainer.service_container.memory_api_service]),
    ],
) -> MessageResponse:
    """重建记忆索引。"""
    await svc.rebuild_index()
    return MessageResponse(message="索引重建完成")
