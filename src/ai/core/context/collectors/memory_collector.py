"""记忆上下文收集器 — 收集 MEMORY.md 索引和相关记忆搜索结果。"""

import logging
from typing import TYPE_CHECKING

from src.ai.core.context.collector import ContextCollector
from src.ai.core.context.types import (
    ContextBuildRequest,
    ContextCollectorResult,
    ContextSection,
)

if TYPE_CHECKING:
    from src.ai.core.memory.service import MemoryService

logger = logging.getLogger(__name__)


class MemoryCollector(ContextCollector):
    """收集记忆上下文。

    从 MemoryService 获取 MEMORY.md 索引内容和关键词搜索结果。
    可缓存（MEMORY.md 索引变化不频繁）。

    Args:
        memory_service: 记忆服务实例。
    """

    def __init__(self, memory_service: "MemoryService") -> None:
        self._memory_service = memory_service

    @property
    def name(self) -> str:
        return "memory"

    async def collect(self, request: ContextBuildRequest) -> ContextCollectorResult:
        if not request.enable_memory:
            return ContextCollectorResult()

        try:
            # MEMORY.md 索引内容
            system_context = self._memory_service.get_context_for_prompt()

            # LLM 相关记忆选择（优先）或关键词搜索
            search_context = ""
            query = self._extract_last_user_message(request.messages)
            if query and query.strip():
                results = await self._memory_service.find_relevant_memories(
                    query, limit=request.memory_search_limit
                )
                if results:
                    lines = ["## 相关记忆", ""]
                    for r in results:
                        lines.append(f"- [{r.entry.memory_type}] {r.entry.description}")
                        if r.entry.content:
                            lines.append(f"  {r.entry.content[:200]}")
                    search_context = "\n".join(lines)

            parts = [p for p in [system_context, search_context] if p]
            if not parts:
                return ContextCollectorResult()

            content = "\n\n".join(parts)
            section = ContextSection(
                name="memory",
                content=content,
                priority=2,
                cacheable=False,  # LLM 选择结果每次不同，不缓存
            )
            return ContextCollectorResult(sections=[section])
        except Exception:
            logger.debug("记忆上下文收集失败", exc_info=True)
            return ContextCollectorResult()

    @staticmethod
    def _extract_last_user_message(messages: list) -> str:
        """从消息列表中提取最后一条用户消息。"""
        for msg in reversed(messages):
            if getattr(msg, "type", "") == "human":
                return msg.content
        return ""
