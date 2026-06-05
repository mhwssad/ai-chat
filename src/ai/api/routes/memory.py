"""记忆路由。"""

from fastapi import APIRouter

from src.ai.api.deps import MemoryServiceDep
from src.ai.api.schemas.common import MessageResponse
from src.ai.api.schemas.memory import (
    MemoryCreateRequest,
    MemoryEntryResponse,
    MemorySearchRequest,
    MemorySearchResultResponse,
    MemoryStatsResponse,
    MemoryStatusRequest,
)
from src.ai.core.memory.types import MEMORY_TYPES, MemoryWriteRequest

router = APIRouter(prefix="/memory", tags=["memory"])


def _entry_to_response(entry) -> MemoryEntryResponse:
    """转换 MemoryEntry 为响应格式。"""
    return MemoryEntryResponse(
        name=entry.name,
        memory_type=entry.memory_type,
        description=entry.description,
        content=entry.content,
        file_path=str(entry.file_path) if entry.file_path else None,
        session_id=entry.session_id,
        scope=entry.scope,
        source_type=entry.source_type,
        source_id=entry.source_id,
        status=entry.status,
        created_at=entry.created_at.isoformat() if entry.created_at else None,
        metadata=entry.metadata,
    )


@router.get("", response_model=list[MemoryEntryResponse])
async def list_memories(
    service: MemoryServiceDep,
    memory_type: str | None = None,
    scope: str | None = None,
    status: str | None = "active",
):
    """列出记忆条目。

    Args:
        memory_type: 按类型过滤（user/feedback/project/reference）。
    """
    type_filter = None
    if memory_type and memory_type in MEMORY_TYPES:
        type_filter = memory_type

    entries = await service.alist_entries(
        memory_type=type_filter,
        scope=scope,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
    )
    return [_entry_to_response(e) for e in entries]


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(service: MemoryServiceDep):
    """获取记忆统计。"""
    stats = await service.aget_stats()
    by_type_val: dict[str, int] | int = stats.get("by_type", {})
    return MemoryStatsResponse(
        total=stats.get("total", 0),
        by_type=by_type_val if isinstance(by_type_val, dict) else {},
    )


@router.get("/{name}", response_model=MemoryEntryResponse)
async def get_memory(name: str, service: MemoryServiceDep):
    """获取记忆。

    Args:
        name: 记忆名称。
    """
    entry = await service.aget(name)
    if entry is None:
        from src.ai.exception.memory_exception import MemoryNotFoundError

        raise MemoryNotFoundError(f"记忆不存在: {name}", context={"name": name})

    return _entry_to_response(entry)


@router.post("", response_model=MemoryEntryResponse)
async def create_memory(
    request: MemoryCreateRequest,
    service: MemoryServiceDep,
):
    """创建记忆。

    Args:
        request: 创建请求。
    """
    write_request = MemoryWriteRequest(
        content=request.content,
        memory_type=request.memory_type,  # type: ignore[arg-type]
        name=request.name,
        description=request.description,
        scope=request.scope,  # type: ignore[arg-type]
        source_type=request.source_type,  # type: ignore[arg-type]
        source_id=request.source_id,
        metadata=request.metadata,
    )
    entry = await service.asave(write_request)
    return _entry_to_response(entry)


@router.delete("/{name}", response_model=MessageResponse)
async def delete_memory(name: str, service: MemoryServiceDep):
    """删除记忆。

    Args:
        name: 记忆名称。
    """
    success = await service.adelete(name)
    if not success:
        from src.ai.exception.memory_exception import MemoryNotFoundError

        raise MemoryNotFoundError(f"记忆不存在: {name}", context={"name": name})

    return MessageResponse(message=f"记忆 {name} 已删除")


@router.post("/{name}/status", response_model=MemoryEntryResponse)
async def set_memory_status(
    name: str,
    request: MemoryStatusRequest,
    service: MemoryServiceDep,
):
    """设置记忆状态。

    Args:
        name: 记忆名称。
        request: 状态请求，支持 active / disabled。
    """
    if request.status == "active":
        success = await service.aenable(name)
    elif request.status == "disabled":
        success = await service.adisable(name)
    else:
        from src.ai.exception.memory_exception import MemoryException

        raise MemoryException(
            "不支持的记忆状态",
            context={"name": name, "status": request.status},
        )

    if not success:
        from src.ai.exception.memory_exception import MemoryNotFoundError

        raise MemoryNotFoundError(f"记忆不存在: {name}", context={"name": name})

    entry = await service.aget(name)
    if entry is None:
        from src.ai.exception.memory_exception import MemoryNotFoundError

        raise MemoryNotFoundError(f"记忆不存在: {name}", context={"name": name})
    return _entry_to_response(entry)


@router.post("/search", response_model=list[MemorySearchResultResponse])
async def search_memories(
    request: MemorySearchRequest,
    service: MemoryServiceDep,
):
    """搜索记忆。

    Args:
        request: 搜索请求。
    """
    results = await service.asearch(request.query, limit=request.limit)

    return [
        MemorySearchResultResponse(
            entry=_entry_to_response(r.entry),
            score=r.score,
            match_type=r.match_type,
        )
        for r in results
    ]
