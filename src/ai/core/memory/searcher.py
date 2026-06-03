"""统一记忆搜索 — 三层搜索架构：向量召回 + 关键词补充 + LLM 精排。

三层搜索：
1. Layer 1: 向量搜索（MemoryVectorStore）— 语义召回 top_k=20
2. Layer 2: 关键词搜索 — 关键词补充 top_k=10
3. Layer 3: LLM 精排 — 仅对候选集调用
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from .types import MemoryEntry, MemorySearchResult

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from .store import MemoryStore
    from .vector_store import MemoryVectorStore

logger = logging.getLogger(__name__)

# 中文停用词
_STOPWORDS = frozenset(
    {
        "",
        "的",
        "了",
        "是",
        "在",
        "有",
        "和",
        "就",
        "不",
        "也",
        "都",
        "要",
        "会",
        "能",
        "这",
        "那",
    }
)


class MemorySearcher:
    """统一记忆搜索。

    三层搜索架构：
    1. 向量召回（语义相似度）
    2. 关键词补充（精确匹配）
    3. LLM 精排（语义相关性判断）

    Args:
        store: 记忆存储。
        llm: 用于精排的 LLM 实例。
        prompt_service: 提示词服务（从 DB 获取提示词模板）。
        max_results: 最多返回的记忆数量。
        vector_store: 向量存储（可选，启用向量搜索）。
    """

    def __init__(
        self,
        store: MemoryStore,
        llm: BaseChatModel,
        prompt_service: object,
        max_results: int = 5,
        vector_store: MemoryVectorStore | None = None,
    ) -> None:
        self._store = store
        self._llm = llm
        self._prompt_service = prompt_service
        self._max_results = max_results
        self._vector_store = vector_store

    # ── 统一入口 ──────────────────────────────────────────────

    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
        use_llm: bool = True,
    ) -> list[MemorySearchResult]:
        """统一搜索入口。

        三层搜索架构：
        1. 向量召回 top_k=20
        2. 关键词补充 top_k=10
        3. LLM 精排（仅对候选集）

        Args:
            query: 用户查询文本。
            limit: 最多返回的记忆数量。
            use_llm: 是否使用 LLM 精排。

        Returns:
            相关记忆搜索结果列表。
        """
        if not query.strip():
            return []

        # Layer 1 + 2: 收集候选集
        candidates = self._collect_candidates(query, limit=limit * 4)

        if not candidates:
            return []

        # Layer 3: LLM 精排
        if use_llm and len(candidates) > limit:
            try:
                results = await self.select(query, candidates)
                if results:
                    return results[:limit]
            except Exception:
                logger.warning("LLM 记忆选择失败，回退到候选集排序", exc_info=True)

        # 回退：按分数排序返回
        return candidates[:limit]

    def _collect_candidates(
        self, query: str, limit: int = 20
    ) -> list[MemorySearchResult]:
        """收集候选集（向量召回 + 关键词补充）。

        Args:
            query: 查询文本。
            limit: 候选集大小。

        Returns:
            候选集（按分数排序，去重）。
        """
        seen_names: set[str] = set()
        candidates: list[MemorySearchResult] = []

        # Layer 1: 向量召回
        if self._vector_store is not None:
            try:
                vector_results = self._vector_store.search(query, top_k=20)
                for vr in vector_results:
                    name = vr.get("id", "")
                    if name in seen_names:
                        continue
                    seen_names.add(name)

                    # 从 store 获取完整 entry
                    entry = self._store.get_by_name(name)
                    if entry is not None:
                        distance = vr.get("distance", 1.0)
                        score = max(0.0, 1.0 - distance)
                        candidates.append(
                            MemorySearchResult(
                                entry=entry, score=score, match_type="vector"
                            )
                        )
            except Exception:
                logger.warning("向量搜索失败，回退到关键词搜索", exc_info=True)

        # Layer 2: 关键词补充
        keyword_results = self.keyword_search(query, limit=10)
        for kr in keyword_results:
            if kr.entry.name not in seen_names:
                seen_names.add(kr.entry.name)
                candidates.append(kr)

        # 按分数排序
        candidates.sort(key=lambda r: r.score, reverse=True)
        return candidates[:limit]

    # ── LLM 精排 ─────────────────────────────────────────────

    async def select(
        self, query: str, candidates: list[MemoryEntry] | list[MemorySearchResult]
    ) -> list[MemorySearchResult]:
        """从候选记忆中选择与查询最相关的子集。

        Args:
            query: 用户查询文本。
            candidates: 候选记忆列表（MemoryEntry 或 MemorySearchResult）。

        Returns:
            相关记忆搜索结果列表。LLM 调用失败时返回空列表。
        """
        if not candidates or not query.strip():
            return []

        # 统一处理输入类型
        entries: list[MemoryEntry] = []
        for c in candidates:
            if isinstance(c, MemorySearchResult):
                entries.append(c.entry)
            else:
                entries.append(c)

        try:
            manifest = self._format_manifest(entries)
            system_prompt = self._render_system_prompt()
            human_input = f"用户问题：{query}\n\n候选记忆清单：\n{manifest}"

            from langchain_core.messages import HumanMessage, SystemMessage

            response = await self._llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=human_input),
                ]
            )

            selected_names = self._parse_response(response.content)  # type: ignore[arg-type]
            if not selected_names:
                return []

            name_to_entry = {e.name: e for e in entries}
            results = []
            for name in selected_names[: self._max_results]:
                entry = name_to_entry.get(name)
                if entry:
                    results.append(
                        MemorySearchResult(
                            entry=entry, score=1.0, match_type="llm_relevance"
                        )
                    )

            logger.debug(
                "LLM 记忆选择：候选 %d 条，选中 %d 条",
                len(entries),
                len(results),
            )
            return results

        except Exception:
            logger.warning("LLM 记忆选择失败，返回空列表", exc_info=True)
            return []

    # ── 关键词搜索 ────────────────────────────────────────────

    def keyword_search(
        self, query: str, *, limit: int = 10
    ) -> list[MemorySearchResult]:
        """关键词搜索记忆内容。

        三级匹配策略（引入时间衰减评分）：
        1. 内容精确包含 → score=1.0
        2. 描述精确包含 → score=0.8
        3. 分词重叠 → score=按重叠比例

        Args:
            query: 搜索查询。
            limit: 最多返回结果数。

        Returns:
            搜索结果列表。
        """
        query_lower = query.lower()
        now = datetime.now(timezone.utc)
        results: list[MemorySearchResult] = []

        for entry in self._store.list_all():
            score = self._score_entry(entry, query_lower)
            if score > 0:
                # 时间衰减：最近访问的记忆获得加分
                decay = self._time_decay(entry, now)
                final_score = score * decay
                results.append(
                    MemorySearchResult(
                        entry=entry, score=final_score, match_type="keyword"
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    # ── 内部工具 ──────────────────────────────────────────────

    @staticmethod
    def _score_entry(entry: MemoryEntry, query_lower: str) -> float:
        """计算单条记忆的关键词匹配分数。"""
        content_lower = entry.content.lower()
        desc_lower = entry.description.lower()

        if query_lower in content_lower:
            return 1.0
        if query_lower in desc_lower:
            return 0.8

        query_terms = set(re.split(r"\W+", query_lower)) - _STOPWORDS
        content_terms = set(re.split(r"\W+", content_lower + " " + desc_lower))
        overlap = len(query_terms & content_terms)
        if overlap > 0:
            return min(overlap / max(len(query_terms), 1) * 0.6, 0.59)

        return 0.0

    @staticmethod
    def _time_decay(entry: MemoryEntry, now: datetime) -> float:
        """计算时间衰减因子。

        最近创建的记忆获得轻微加分（最高 1.1 倍），
        老旧记忆略微降分（最低 0.9 倍）。

        Args:
            entry: 记忆条目。
            now: 当前时间。

        Returns:
            衰减因子（0.9 ~ 1.1）。
        """
        if entry.created_at is None:
            return 1.0

        try:
            age_days = (now - entry.created_at).total_seconds() / 86400
            if age_days < 0:
                return 1.0
            # 30 天内线性衰减：0 天 → 1.1，30 天 → 1.0，>30 天 → 0.95
            if age_days <= 30:
                return 1.1 - (age_days / 30) * 0.1
            return 0.95
        except Exception:
            return 1.0

    def _render_system_prompt(self) -> str:
        """从 prompt_service 渲染系统提示词。"""
        from src.ai.core.prompts import PromptRenderRequest

        result = self._prompt_service.render(  # type: ignore[attr-defined]
            PromptRenderRequest(
                prompt_key="memory.relevance_select",
                variables={"max_results": self._max_results},
            )
        )
        return result.content

    @staticmethod
    def _format_manifest(candidates: list[MemoryEntry]) -> str:
        """将候选记忆格式化为清单。"""
        lines = []
        for i, entry in enumerate(candidates, 1):
            lines.append(
                f"{i}. [{entry.memory_type}] {entry.name}: {entry.description}"
            )
        return "\n".join(lines)

    @staticmethod
    def _parse_response(response: str) -> list[str]:
        """解析 LLM 返回的 JSON 数组。"""
        text = response.strip()
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1:
            return []
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, list):
                return [str(name) for name in parsed if isinstance(name, str)]
        except json.JSONDecodeError:
            logger.debug("LLM 返回的 JSON 解析失败: %s", text[:200])
        return []
