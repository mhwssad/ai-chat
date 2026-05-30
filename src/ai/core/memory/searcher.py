"""统一记忆搜索 — 关键词召回 + LLM 精排。

提供两种搜索模式：
1. keyword_search(): 纯关键词匹配，适合低延迟场景
2. search(): 关键词召回 + LLM 精排，适合高质量检索
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from .types import MemoryEntry, MemorySearchResult

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from .store import MemoryStore

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

    组合关键词匹配和 LLM 相关性选择，提供单一搜索入口。

    Args:
        store: 记忆存储。
        llm: 用于精排的 LLM 实例。
        prompt_service: 提示词服务（从 DB 获取提示词模板）。
        max_results: 最多返回的记忆数量。
    """

    def __init__(
        self,
        store: MemoryStore,
        llm: BaseChatModel,
        prompt_service: object,
        max_results: int = 5,
    ) -> None:
        self._store = store
        self._llm = llm
        self._prompt_service = prompt_service
        self._max_results = max_results

    # ── 统一入口 ──────────────────────────────────────────────

    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
        use_llm: bool = True,
    ) -> list[MemorySearchResult]:
        """统一搜索入口。

        优先使用 LLM 进行语义级相关性判断，
        失败时回退到关键词搜索。

        Args:
            query: 用户查询文本。
            limit: 最多返回的记忆数量。
            use_llm: 是否使用 LLM 精排。

        Returns:
            相关记忆搜索结果列表。
        """
        if not query.strip():
            return []

        if use_llm:
            candidates = self._store.list_all()
            if not candidates:
                return []
            try:
                results = await self.select(query, candidates)
                if results:
                    return results[:limit]
            except Exception:
                logger.warning("LLM 记忆选择失败，回退到关键词搜索", exc_info=True)

        return self.keyword_search(query, limit=limit)

    # ── LLM 精排 ─────────────────────────────────────────────

    async def select(
        self, query: str, candidates: list[MemoryEntry]
    ) -> list[MemorySearchResult]:
        """从候选记忆中选择与查询最相关的子集。

        Args:
            query: 用户查询文本。
            candidates: 候选记忆列表。

        Returns:
            相关记忆搜索结果列表。LLM 调用失败时返回空列表。
        """
        if not candidates or not query.strip():
            return []

        try:
            manifest = self._format_manifest(candidates)
            system_prompt = self._render_system_prompt()
            human_input = f"用户问题：{query}\n\n候选记忆清单：\n{manifest}"

            from langchain_core.messages import HumanMessage, SystemMessage

            response = await self._llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=human_input),
                ]
            )

            selected_names = self._parse_response(response.content)
            if not selected_names:
                return []

            name_to_entry = {e.name: e for e in candidates}
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
                len(candidates),
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

        三级匹配策略：
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
        results: list[MemorySearchResult] = []

        for entry in self._store.list_all():
            score = self._score_entry(entry, query_lower)
            if score > 0:
                results.append(
                    MemorySearchResult(entry=entry, score=score, match_type="keyword")
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

    def _render_system_prompt(self) -> str:
        """从 prompt_service 渲染系统提示词。"""
        from src.ai.core.prompts import PromptRenderRequest

        result = self._prompt_service.render(
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
