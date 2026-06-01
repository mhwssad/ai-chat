"""统一记忆服务 — 集成文件系统记忆的 CRUD、搜索和提取。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .types import (
    MemoryEntry,
    MemorySearchResult,
    MemoryType,
    MemoryWriteRequest,
    generate_memory_name,
)

if TYPE_CHECKING:
    from .extractor import MemoryExtractor
    from .prompt import MemoryPromptBuilder
    from .searcher import MemorySearcher
    from .store import MemoryStore
    from .vector_store import MemoryVectorStore

logger = logging.getLogger(__name__)

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
    """

    def __init__(
        self,
        *,
        store: MemoryStore,
        extractor: MemoryExtractor,
        prompt_builder: MemoryPromptBuilder,
        searcher: MemorySearcher,
        vector_store: MemoryVectorStore | None = None,
    ) -> None:
        self._store = store
        self._extractor = extractor
        self._prompt = prompt_builder
        self._searcher = searcher
        self._vector_store = vector_store

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
            created_at=entry.created_at,
            metadata=entry.metadata,
        )

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
        return self._store.get_by_name(name)

    def delete(self, name: str) -> bool:
        """删除记忆。"""
        success = self._store.delete(name)
        if success:
            # 同步删除向量索引
            if self._vector_store is not None:
                try:
                    self._vector_store.delete_entry(name)
                except Exception:
                    logger.debug("向量索引删除失败: %s", name, exc_info=True)
            logger.info("记忆已删除: %s", name)
        return success

    def list_entries(
        self, *, memory_type: MemoryType | None = None
    ) -> list[MemoryEntry]:
        """列出记忆条目。"""
        if memory_type:
            return self._store.list_by_type(memory_type)
        return self._store.list_all()

    # ── 搜索（委托给 MemorySearcher） ────────────────────────

    def search(self, query: str, *, limit: int = 5) -> list[MemorySearchResult]:
        """关键词搜索记忆。"""
        return self._searcher.keyword_search(query, limit=limit)

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
