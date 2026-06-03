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
)
from src.ai.core.memory.types import MemoryWriteRequest

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
        created_at=entry.created_at.isoformat() if entry.created_at else None,
        metadata=entry.metadata,
    )


@router.get("", response_model=list[MemoryEntryResponse])
async def list_memories(
    service: MemoryServiceDep,
    memory_type: str | None = None,
):
    """列出记忆条目。

    Args:
        memory_type: 按类型过滤（user/feedback/project/reference）。
    """
    from src.ai.core.memory.types import MEMORY_TYPES

    type_filter = None
    if memory_type and memory_type in MEMORY_TYPES:
        type_filter = memory_type

    entries = service.list_entries(memory_type=type_filter)
    return [_entry_to_response(e) for e in entries]


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(service: MemoryServiceDep):
    """获取记忆统计。"""
    stats = service.get_stats()
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
    entry = service.get(name)
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
        metadata=request.metadata,
    )
    entry = service.save(write_request)
    return _entry_to_response(entry)


@router.delete("/{name}", response_model=MessageResponse)
async def delete_memory(name: str, service: MemoryServiceDep):
    """删除记忆。

    Args:
        name: 记忆名称。
    """
    success = service.delete(name)
    if not success:
        from src.ai.exception.memory_exception import MemoryNotFoundError

        raise MemoryNotFoundError(f"记忆不存在: {name}", context={"name": name})

    return MessageResponse(message=f"记忆 {name} 已删除")


@router.post("/search", response_model=list[MemorySearchResultResponse])
async def search_memories(
    request: MemorySearchRequest,
    service: MemoryServiceDep,
):
    """搜索记忆。

    Args:
        request: 搜索请求。
    """
    results = service.search(request.query, limit=request.limit)

    return [
        MemorySearchResultResponse(
            entry=_entry_to_response(r.entry),
            score=r.score,
            match_type=r.match_type,
        )
        for r in results
    ]
