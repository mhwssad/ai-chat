"""记忆生命周期管理 — 自动过期、语义去重和合并。"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from .store import MemoryStore
    from .vector_store import MemoryVectorStore

logger = logging.getLogger(__name__)


class MemoryLifecycleManager:
    """记忆生命周期管理器。

    自动维护记忆库的健康状态：
    - 过期清理：超过 30 天未访问且访问次数少的记忆标记过期
    - 语义去重：Embedding 相似度 > 0.9 的配对保留较新的
    - 相似合并：同一 memory_type 且主题相近的记忆使用 LLM 摘要合并

    Args:
        store: 记忆存储。
        vector_store: 向量存储（用于语义去重）。
        llm: LLM 实例（用于合并摘要）。
        expire_days: 过期天数（默认 30）。
        expire_min_access: 最小访问次数阈值（默认 3）。
        dedup_threshold: 去重相似度阈值（默认 0.9）。
    """

    def __init__(
        self,
        *,
        store: MemoryStore,
        vector_store: MemoryVectorStore | None = None,
        llm: BaseChatModel | None = None,
        expire_days: int = 30,
        expire_min_access: int = 3,
        dedup_threshold: float = 0.9,
    ) -> None:
        self._store = store
        self._vector_store = vector_store
        self._llm = llm
        self._expire_days = expire_days
        self._expire_min_access = expire_min_access
        self._dedup_threshold = dedup_threshold

    async def run_maintenance(self) -> dict[str, int]:
        """执行完整维护周期。

        Returns:
            各阶段处理数量的统计字典。
        """
        stats: dict[str, int] = {
            "expired": 0,
            "deduplicated": 0,
            "merged": 0,
        }

        # 1. 过期清理
        stats["expired"] = self._expire_stale()

        # 2. 语义去重
        if self._vector_store is not None:
            stats["deduplicated"] = await self._deduplicate_semantic()

        # 3. 相似合并
        if self._llm is not None:
            stats["merged"] = await self._merge_similar()

        logger.info("记忆维护完成: %s", stats)
        return stats

    def _expire_stale(self) -> int:
        """清理过期记忆。

        超过 expire_days 天未创建且 access_count < expire_min_access 的记忆将被删除。

        Returns:
            删除的记忆数量。
        """
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(days=self._expire_days)
        entries = self._store.list_all()
        expired = 0

        for entry in entries:
            # 检查创建时间
            if entry.created_at is None:
                continue
            if entry.created_at > threshold:
                continue

            # 检查访问次数
            access_count = entry.metadata.get("access_count", 0)
            if access_count >= self._expire_min_access:
                continue

            # 删除过期记忆
            try:
                self._store.delete(entry.name)
                expired += 1
                logger.debug("记忆已过期: %s", entry.name)
            except Exception:
                logger.warning("删除过期记忆失败: %s", entry.name, exc_info=True)

        return expired

    async def _deduplicate_semantic(self) -> int:
        """语义去重：使用 Embedding 相似度检测重复记忆。

        相似度 > dedup_threshold 的配对保留较新的。

        Returns:
            删除的记忆数量。
        """
        if self._vector_store is None:
            return 0

        entries = self._store.list_all()
        if len(entries) < 2:
            return 0

        to_delete: set[str] = set()
        deduplicated = 0

        # 使用向量搜索查找相似记忆对
        for entry in entries:
            if entry.name in to_delete:
                continue

            # 搜索与当前记忆相似的其他记忆
            query = f"{entry.description} {entry.content[:200]}"
            similar = self._vector_store.search(query, top_k=5)

            for sim in similar:
                sim_name = sim.get("id", "")
                distance = sim.get("distance", 1.0)
                similarity = 1.0 - distance

                if sim_name == entry.name or sim_name in to_delete:
                    continue

                if similarity >= self._dedup_threshold:
                    # 找到重复记忆，保留较新的
                    sim_entry = self._store.get_by_name(sim_name)
                    if sim_entry is None:
                        continue

                    # 比较创建时间，保留较新的
                    if self._is_older(entry, sim_entry):
                        to_delete.add(entry.name)
                    else:
                        to_delete.add(sim_name)
                    deduplicated += 1

        # 执行删除
        for name in to_delete:
            try:
                self._store.delete(name)
            except Exception:
                logger.warning("删除重复记忆失败: %s", name, exc_info=True)

        return deduplicated

    async def _merge_similar(self) -> int:
        """合并相似记忆。

        同一 memory_type 且主题相近的记忆使用 LLM 摘要合并。

        Returns:
            合并的次数。
        """
        if self._llm is None:
            return 0

        entries = self._store.list_all()
        if len(entries) < 2:
            return 0

        # 按 memory_type 分组
        groups: dict[str, list] = {}
        for entry in entries:
            groups.setdefault(entry.memory_type, []).append(entry)

        merged = 0
        for memory_type, group in groups.items():
            if len(group) < 2:
                continue

            # 简单配对检查（基于内容相似度）
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a, b = group[i], group[j]
                    if self._content_similar(a.content, b.content):
                        try:
                            await self._merge_entries(a, b)
                            merged += 1
                        except Exception:
                            logger.warning(
                                "合并记忆失败: %s + %s", a.name, b.name, exc_info=True
                            )

        return merged

    async def _merge_entries(self, a: Any, b: Any) -> None:
        """使用 LLM 合并两条记忆。

        Args:
            a: 第一条记忆。
            b: 第二条记忆。
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        from .types import MemoryEntry

        prompt = (
            "请将以下两条记忆合并为一条简洁的记忆。"
            "保留所有重要信息，去除重复内容。\n\n"
            f"记忆 1: {a.content}\n\n"
            f"记忆 2: {b.content}\n\n"
            "合并结果（只输出合并后的内容）："
        )

        response = await self._llm.ainvoke(  # type: ignore[union-attr]
            [
                SystemMessage(content="你是一个记忆整理助手。"),
                HumanMessage(content=prompt),
            ]
        )

        merged_content = response.content.strip()  # type: ignore[union-attr]
        if not merged_content:
            return

        # 确定保留哪条记忆（保留较新的）
        if self._is_older(a, b):
            keep, remove = b, a
        else:
            keep, remove = a, b

        # 删除较旧的记忆
        self._store.delete(remove.name)

        # 删除较新的记忆（随后用合并内容重新写入）
        self._store.delete(keep.name)

        # 用合并后的内容重新写入保留条目
        merged_entry = MemoryEntry(
            name=keep.name,
            memory_type=keep.memory_type,
            description=keep.description,
            content=merged_content,
            session_id=keep.session_id,
            created_at=keep.created_at,
            metadata=keep.metadata,
        )
        self._store.write(merged_entry)

    @staticmethod
    def _is_older(a: Any, b: Any) -> bool:
        """判断 a 是否比 b 更旧。"""
        a_time = a.created_at or datetime.min.replace(tzinfo=timezone.utc)
        b_time = b.created_at or datetime.min.replace(tzinfo=timezone.utc)
        return a_time < b_time

    @staticmethod
    def _content_similar(a: str, b: str) -> bool:
        """简单的内容相似度检查（基于词汇重叠率）。"""
        words_a = set(re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", a.lower()))
        words_b = set(re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", b.lower()))
        if not words_a or not words_b:
            return False
        overlap = len(words_a & words_b)
        min_size = min(len(words_a), len(words_b))
        return overlap / min_size > 0.6
