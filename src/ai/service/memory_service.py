"""记忆 API 服务 — MemoryService 的薄包装。

共享服务层，API 路由统一使用。
"""

from __future__ import annotations

from dataclasses import asdict
from src.ai.config.logging_setup import get_logger
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.ai.utils.thread_pool import ThreadPoolManager

logger = get_logger(__name__)


class MemoryApiService:
    """记忆 API 服务。

    职责：
    1. 记忆 CRUD（保存、获取、删除、禁用、启用）
    2. 记忆搜索和语义检索
    3. 从对话中提取记忆
    4. 索引维护和统计
    """

    def __init__(
        self,
        *,
        memory_service: Any,
        thread_pool: ThreadPoolManager | None = None,
    ) -> None:
        self._svc = memory_service
        self._thread_pool = thread_pool

    def _get_pool(self) -> ThreadPoolManager:
        """获取线程池实例。"""
        if self._thread_pool is None:
            from src.ai.utils.thread_pool import get_thread_pool

            self._thread_pool = get_thread_pool()
        return self._thread_pool

    # ── CRUD ──────────────────────────────────────────────────

    async def save(
        self,
        *,
        content: str,
        memory_type: str = "project",
        name: str | None = None,
        description: str | None = None,
        scope: str = "project",
        source_type: str = "manual",
        source_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """保存记忆条目。"""
        entry = await self._get_pool().run_io(
            self._svc.save,
            content=content,
            memory_type=memory_type,
            name=name,
            description=description,
            scope=scope,
            source_type=source_type,
            source_id=source_id,
            metadata=metadata or {},
        )
        return self._entry_to_dict(entry)

    async def get(self, name: str) -> dict[str, Any] | None:
        """获取指定记忆条目。"""
        entry = await self._get_pool().run_io(self._svc.get, name)
        if entry is None:
            return None
        return self._entry_to_dict(entry)

    async def delete(self, name: str) -> None:
        """删除记忆条目。"""
        await self._get_pool().run_io(self._svc.delete, name)

    async def disable(self, name: str) -> None:
        """禁用记忆条目。"""
        await self._get_pool().run_io(self._svc.disable, name)

    async def enable(self, name: str) -> None:
        """启用记忆条目。"""
        await self._get_pool().run_io(self._svc.enable, name)

    async def list_entries(
        self,
        *,
        memory_type: str | None = None,
        scope: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """列出记忆条目。"""
        entries = await self._get_pool().run_io(
            self._svc.list_entries,
            memory_type=memory_type,
            scope=scope,
            status=status,
        )
        return [self._entry_to_dict(e) for e in entries]

    # ── 搜索 ──────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """搜索记忆条目。"""
        results = await self._get_pool().run_io(self._svc.search, query, limit=limit)
        return [
            {
                "entry": self._entry_to_dict(r.entry),
                "score": r.score,
                "match_type": r.match_type,
            }
            for r in results
        ]

    async def extract_from_conversation(
        self,
        user_message: str,
        assistant_message: str,
    ) -> list[dict[str, Any]]:
        """从对话中提取记忆。"""
        requests = await self._svc.aextract_from_conversation(
            user_message,
            assistant_message,
        )
        return [asdict(r) for r in requests]

    # ── 维护 ──────────────────────────────────────────────────

    async def rebuild_index(self) -> None:
        """重建记忆索引。"""
        await self._get_pool().run_io(self._svc.rebuild_index)

    async def get_stats(self) -> dict[str, Any]:
        """获取记忆统计信息。"""
        return await self._get_pool().run_io(self._svc.get_stats)

    # ── 内部工具 ──────────────────────────────────────────────

    @staticmethod
    def _entry_to_dict(entry: Any) -> dict[str, Any]:
        """将 MemoryEntry 转换为字典。"""
        return asdict(entry)
