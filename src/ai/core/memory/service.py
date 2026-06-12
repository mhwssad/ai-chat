"""统一记忆服务 — 集成文件系统记忆的 CRUD、搜索和提取。"""

from __future__ import annotations

import json
from src.ai.config.logging_setup import get_logger
from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING

from sqlmodel import Session

from src.ai.storage.runtime_repository import MemoryEntryRepository
from src.ai.utils.redaction import redact_for_audit

from .types import (
    MemoryEntry,
    MemorySearchResult,
    MemoryScope,
    MemorySourceType,
    MemoryStatus,
    MemoryType,
    MemoryWriteRequest,
    generate_memory_name,
)

if TYPE_CHECKING:
    from src.ai.utils.thread_pool import ThreadPoolManager

    from .extractor import MemoryExtractor
    from .prompt import MemoryPromptBuilder
    from .searcher import MemorySearcher
    from .store import MemoryStore
    from .vector_store import MemoryVectorStore

logger = get_logger(__name__)

# 触发自动维护的记忆数量阈值
_AUTO_MAINTENANCE_THRESHOLD = 500


class MemoryService:
    """统一记忆服务。

    职责：
    - 记忆 CRUD（save/get/delete/list）
    - 搜索代理（委托给 MemorySearcher）
    - 从对话提取记忆（委托给 MemoryExtractor）
    - 构建系统 prompt 上下文（委托给 MemoryPromptBuilder）
    - 向量索引同步

    Args:
        store: 文件系统记忆存储。
        extractor: 记忆提取器。
        prompt_builder: 记忆提示构建器。
        searcher: 统一搜索器。
        vector_store: 向量存储（可选）。
        thread_pool: 统一线程池管理器（可选，用于异步包装同步 IO）。
    """

    def __init__(
        self,
        *,
        store: MemoryStore,
        extractor: MemoryExtractor,
        prompt_builder: MemoryPromptBuilder,
        searcher: MemorySearcher,
        vector_store: MemoryVectorStore | None = None,
        thread_pool: ThreadPoolManager | None = None,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        self._store = store
        self._extractor = extractor
        self._prompt = prompt_builder
        self._searcher = searcher
        self._vector_store = vector_store
        self._thread_pool = thread_pool
        self._session_factory = session_factory

    @property
    def store(self) -> MemoryStore:
        return self._store

    # ── CRUD ──────────────────────────────────────────────────

    def save(
        self, request: MemoryWriteRequest, *, session_id: str | None = None
    ) -> MemoryEntry:
        """保存记忆到文件系统。"""
        if not request.name:
            request.name = generate_memory_name(
                request.memory_type, request.content, with_hash=True
            )

        if not request.description:
            request.description = request.content[:120].replace("\n", " ")

        entry = MemoryEntry(
            name=request.name,
            memory_type=request.memory_type,
            description=request.description,
            content=request.content,
            session_id=session_id,
            scope=request.scope,
            source_type=request.source_type,
            source_id=request.source_id,
            status="active",
            metadata=request.metadata,
        )

        file_path = self._store.write(entry)
        entry = MemoryEntry(
            name=entry.name,
            memory_type=entry.memory_type,
            description=entry.description,
            content=entry.content,
            file_path=file_path,
            session_id=session_id,
            scope=entry.scope,
            source_type=entry.source_type,
            source_id=entry.source_id,
            status=entry.status,
            created_at=entry.created_at,
            metadata=entry.metadata,
        )
        self._sync_control_record(entry)

        # 同步向量索引
        if self._vector_store is not None:
            try:
                self._vector_store.index_entry(entry)
            except Exception:
                logger.debug("向量索引同步失败: %s", entry.name, exc_info=True)

        logger.info(
            "记忆已保存: %s (%s) [session=%s]",
            entry.name,
            entry.memory_type,
            session_id or "default",
        )
        return entry

    def get(self, name: str) -> MemoryEntry | None:
        """按 name 获取单个记忆。"""
        entry = self._store.get_by_name(name)
        if entry is None:
            return None
        return self._apply_control_state([entry])[0]

    def delete(self, name: str) -> bool:
        """删除记忆。"""
        success = self._store.delete(name)
        if success:
            self._set_control_status(name, "deleted")
            # 同步删除向量索引
            if self._vector_store is not None:
                try:
                    self._vector_store.delete_entry(name)
                except Exception:
                    logger.debug("向量索引删除失败: %s", name, exc_info=True)
            logger.info("记忆已删除: %s", name)
        return success

    def disable(self, name: str) -> bool:
        """禁用记忆，保留文件内容和索引元信息。"""
        entry = self._store.get_by_name(name)
        if entry is None:
            return False
        self._set_control_status(name, "disabled")
        if self._vector_store is not None:
            try:
                self._vector_store.delete_entry(name)
            except Exception:
                logger.debug("向量索引禁用同步失败: %s", name, exc_info=True)
        logger.info("记忆已禁用: %s", name)
        return True

    def enable(self, name: str) -> bool:
        """启用记忆。"""
        entry = self._store.get_by_name(name)
        if entry is None:
            return False
        self._set_control_status(name, "active")
        if self._vector_store is not None:
            try:
                self._vector_store.index_entry(entry)
            except Exception:
                logger.debug("向量索引启用同步失败: %s", name, exc_info=True)
        logger.info("记忆已启用: %s", name)
        return True

    def list_entries(
        self,
        *,
        memory_type: MemoryType | None = None,
        scope: MemoryScope | None = None,
        status: MemoryStatus | None = "active",
    ) -> list[MemoryEntry]:
        """列出记忆条目。"""
        if memory_type:
            entries = self._store.list_by_type(memory_type)
        else:
            entries = self._store.list_all()
        entries = self._apply_control_state(entries)
        if scope is not None:
            entries = [entry for entry in entries if entry.scope == scope]
        if status is not None:
            entries = [entry for entry in entries if entry.status == status]
        return entries

    # ── 搜索（委托给 MemorySearcher） ────────────────────────

    def search(self, query: str, *, limit: int = 5) -> list[MemorySearchResult]:
        """关键词搜索记忆。"""
        results = self._searcher.keyword_search(query, limit=limit * 2)
        filtered = [
            MemorySearchResult(
                entry=self._apply_control_state([result.entry])[0],
                score=result.score,
                match_type=result.match_type,
            )
            for result in results
        ]
        return [result for result in filtered if result.entry.status == "active"][:limit]

    async def find_relevant_memories(
        self,
        query: str,
        *,
        limit: int = 5,
        fallback_to_keyword: bool = True,
    ) -> list[MemorySearchResult]:
        """使用 LLM 从候选记忆中选择最相关的子集。

        优先使用 LLM 进行语义级相关性判断，
        失败时回退到关键词搜索。

        Args:
            query: 用户查询文本。
            limit: 最多返回的记忆数量。
            fallback_to_keyword: LLM 失败时是否回退到关键词搜索。

        Returns:
            相关记忆搜索结果列表。
        """
        return await self._searcher.search(
            query, limit=limit, use_llm=fallback_to_keyword
        )

    # ── 提取（委托给 MemoryExtractor） ────────────────────────

    def extract_from_conversation(
        self, user_msg: str, assistant_msg: str
    ) -> list[MemoryWriteRequest]:
        """从对话中提取候选记忆（快速模式）。"""
        combined = f"{user_msg}\n{assistant_msg}"
        return self._extractor.extract(combined)

    async def aextract_from_conversation(
        self, user_msg: str, assistant_msg: str
    ) -> list[MemoryWriteRequest]:
        """从对话中提取候选记忆（增强模式，使用 LLM）。"""
        combined = f"{user_msg}\n{assistant_msg}"
        return await self._extractor.aextract_with_llm(combined)

    def save_extracted(
        self, candidates: list[MemoryWriteRequest], *, session_id: str | None = None
    ) -> int:
        """保存提取的候选记忆。"""
        saved = 0
        existing_names = {e.name for e in self._store.list_all()}
        for candidate in candidates:
            if candidate.name in existing_names:
                continue
            try:
                self.save(candidate, session_id=session_id)
                saved += 1
            except Exception:
                logger.debug("保存候选记忆失败: %s", candidate.name, exc_info=True)
        return saved

    # ── 上下文（memory_collector 依赖） ───────────────────────

    def get_context_for_prompt(self) -> str:
        """获取注入系统 prompt 的记忆上下文（MEMORY.md 内容）。"""
        index_content = self._store.index.read()
        if not index_content.strip():
            return ""
        return self._prompt.build_system_context(index_content)

    # ── 索引管理 ──────────────────────────────────────────────

    def rebuild_index(self) -> None:
        """重建 MEMORY.md 索引。"""
        self._store.index.rebuild(self._store.list_all())

    def get_stats(self) -> dict[str, int]:
        """获取记忆统计。"""
        from .store import MemoryIndex

        return MemoryIndex.compute_stats(self._store.list_all())

    # ── 自动维护 ──────────────────────────────────────────────

    async def auto_maintenance(self) -> dict[str, int]:
        """执行自动维护（过期、去重、合并）。

        Returns:
            各阶段处理数量的统计字典。
        """
        from .lifecycle import MemoryLifecycleManager

        manager = MemoryLifecycleManager(
            store=self._store,
            vector_store=self._vector_store,
        )
        return await manager.run_maintenance()

    # ── 异步包装（线程池执行同步 IO） ──────────────────────────

    def _get_pool(self) -> ThreadPoolManager:
        """获取线程池实例。"""
        if self._thread_pool is None:
            from src.ai.utils.thread_pool import get_thread_pool

            self._thread_pool = get_thread_pool()
        return self._thread_pool

    async def asave(
        self, request: MemoryWriteRequest, *, session_id: str | None = None
    ) -> MemoryEntry:
        """异步保存记忆到文件系统。"""
        return await self._get_pool().run_io(self.save, request, session_id=session_id)

    async def aget(self, name: str) -> MemoryEntry | None:
        """异步按 name 获取单个记忆。"""
        return await self._get_pool().run_io(self.get, name)

    async def adelete(self, name: str) -> bool:
        """异步删除记忆。"""
        return await self._get_pool().run_io(self.delete, name)

    async def adisable(self, name: str) -> bool:
        """异步禁用记忆。"""
        return await self._get_pool().run_io(self.disable, name)

    async def aenable(self, name: str) -> bool:
        """异步启用记忆。"""
        return await self._get_pool().run_io(self.enable, name)

    async def alist_entries(
        self,
        *,
        memory_type: MemoryType | None = None,
        scope: MemoryScope | None = None,
        status: MemoryStatus | None = "active",
    ) -> list[MemoryEntry]:
        """异步列出记忆条目。"""
        return await self._get_pool().run_io(
            self.list_entries,
            memory_type=memory_type,
            scope=scope,
            status=status,
        )

    async def asearch(self, query: str, *, limit: int = 5) -> list[MemorySearchResult]:
        """异步关键词搜索记忆。"""
        return await self._get_pool().run_io(self.search, query, limit=limit)

    async def asave_extracted(
        self, candidates: list[MemoryWriteRequest], *, session_id: str | None = None
    ) -> int:
        """异步保存提取的候选记忆。"""
        return await self._get_pool().run_io(
            self.save_extracted, candidates, session_id=session_id
        )

    async def arebuild_index(self) -> None:
        """异步重建 MEMORY.md 索引。"""
        return await self._get_pool().run_io(self.rebuild_index)

    async def aget_stats(self) -> dict[str, int]:
        """异步获取记忆统计。"""
        return await self._get_pool().run_io(self.get_stats)

    async def aget_context_for_prompt(self) -> str:
        """异步获取注入系统 prompt 的记忆上下文。"""
        return await self._get_pool().run_io(self.get_context_for_prompt)

    # ── 控制面同步 ───────────────────────────────────────────

    def _sync_control_record(self, entry: MemoryEntry) -> None:
        """同步记忆控制面元信息。"""
        if self._session_factory is None:
            return
        try:
            with self._session_factory() as session:
                repo = MemoryEntryRepository(session)
                record = repo.get_by_source_id(entry.name)
                payload = {
                    "session_id": entry.session_id,
                    "scope": entry.scope,
                    "memory_type": entry.memory_type,
                    "source_type": entry.source_type,
                    "source_id": entry.name,
                    "content_summary": redact_for_audit(entry.description, max_length=500),
                    "content_ref": str(entry.file_path) if entry.file_path else None,
                    "status": entry.status,
                    "extra": json.dumps(
                        {
                            "source_id": entry.source_id,
                            "name": entry.name,
                            "metadata": entry.metadata,
                        },
                        ensure_ascii=False,
                        default=str,
                    ),
                }
                if record is None:
                    repo.create(**payload)
                else:
                    repo.update(record, **payload)
                session.commit()
        except Exception:
            logger.debug("同步记忆控制面失败: %s", entry.name, exc_info=True)

    def _set_control_status(self, name: str, status: MemoryStatus) -> None:
        """更新控制面状态。"""
        if self._session_factory is None:
            return
        try:
            with self._session_factory() as session:
                repo = MemoryEntryRepository(session)
                record = repo.get_by_source_id(name)
                if record is not None:
                    repo.update(record, status=status)
                    session.commit()
        except Exception:
            logger.debug("更新记忆控制面状态失败: %s", name, exc_info=True)

    def _control_state(self) -> dict[str, dict[str, str | None]]:
        """读取控制面状态映射。"""
        if self._session_factory is None:
            return {}
        try:
            with self._session_factory() as session:
                rows = MemoryEntryRepository(session).list(
                    limit=10000,
                    order_by="updated_at",
                    descending=True,
                )
        except Exception:
            logger.debug("读取记忆控制面失败", exc_info=True)
            return {}
        return {
            row.source_id or "": {
                "scope": row.scope,
                "source_type": row.source_type,
                "status": row.status,
            }
            for row in rows
            if row.source_id
        }

    def _apply_control_state(self, entries: list[MemoryEntry]) -> list[MemoryEntry]:
        """将控制面状态合并到文件系统条目。"""
        state = self._control_state()
        merged: list[MemoryEntry] = []
        for entry in entries:
            row = state.get(entry.name)
            if row is None:
                merged.append(entry)
                continue
            merged.append(
                replace(
                    entry,
                    scope=row.get("scope") or entry.scope,  # type: ignore[arg-type]
                    source_type=row.get("source_type") or entry.source_type,  # type: ignore[arg-type]
                    status=row.get("status") or entry.status,  # type: ignore[arg-type]
                )
            )
        return merged
