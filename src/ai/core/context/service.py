"""上下文服务 — 整合收集、组装、压缩的门面。"""

from __future__ import annotations

from src.ai.config.logging_setup import get_logger
from typing import Any

from src.ai.core.context.assembler import ContextAssembler
from src.ai.core.context.collector import ContextCoordinator
from src.ai.core.context.compact import MicroCompact
from src.ai.core.context.restore import ContextRestorer
from src.ai.core.context.sections import SystemPromptSections
from src.ai.core.context.strategies.base import BaseMemoryStrategy
from src.ai.core.context.types import (
    ContextBuildRequest,
    ContextBuildResult,
    ContextSourceBudget,
    ContextSourceSummary,
)
from src.ai.utils.redaction import redact_for_audit

logger = get_logger(__name__)


class ContextService:
    """上下文服务。

    替代原 ContextBuilder，整合收集器并行收集、段缓存、
    token 预算执行和微压缩。

    Args:
        coordinator: 并行收集协调器。
        assembler: token 预算组装器。
        sections: 段缓存管理器。
        strategy: 记忆策略（负责消息历史管理）。
        micro_compact: 微压缩器（可选）。
        restorer: 上下文恢复器（可选）。
    """

    def __init__(
        self,
        coordinator: ContextCoordinator,
        assembler: ContextAssembler,
        sections: SystemPromptSections,
        strategy: BaseMemoryStrategy,
        micro_compact: MicroCompact,
        restorer: ContextRestorer | None = None,
    ) -> None:
        self._coordinator = coordinator
        self._assembler = assembler
        self._sections = sections
        self._strategy = strategy
        self._micro_compact = micro_compact
        self._restorer = restorer

    @property
    def strategy(self) -> BaseMemoryStrategy:
        """当前使用的记忆策略。"""
        return self._strategy

    @strategy.setter
    def strategy(self, value: BaseMemoryStrategy) -> None:
        self._strategy = value

    async def abuild(self, request: ContextBuildRequest) -> ContextBuildResult:
        """异步构建上下文。

        流程：并行收集 → 段缓存 → token 预算 → 策略构建 → 微压缩。

        Args:
            request: 上下文构建请求。

        Returns:
            构建结果。
        """
        # 1. 并行收集所有上下文段
        sections = await self._coordinator.collect_all(request)

        # 2. token 预算裁剪
        system_prompt, budget_report, total_tokens = self._assembler.assemble(
            sections, request
        )

        # 3. 策略构建上下文消息（管理对话历史）
        context_messages = await self._strategy.abuild_context_messages(
            session_id=request.session_id,
            system_prompt=system_prompt,
        )

        # 4. 压缩后上下文恢复
        restored = None
        if self._restorer and request.session_id:
            restored = await self._restore_context(request.session_id)
            if restored and restored.plan:
                # 将恢复的计划注入到系统提示之后
                from langchain_core.messages import SystemMessage

                restore_msg = SystemMessage(
                    content=f"## 压缩摘要恢复的上下文\n\n{restored.to_system_message()}"
                )
                # 插入到系统消息之后、历史消息之前
                insert_pos = (
                    1
                    if context_messages
                    and getattr(context_messages[0], "type", "") == "system"
                    else 0
                )
                context_messages = list(context_messages)
                context_messages.insert(insert_pos, restore_msg)

        # 5. 合并消息：策略消息 + 当前请求消息
        final_messages: list[Any] = list(context_messages)
        if request.messages:
            final_messages.extend(request.messages)

        # 6. 微压缩（清理旧工具结果 + 截断过长内容）
        final_messages = self._micro_compact.compact(final_messages)

        return ContextBuildResult(
            messages=final_messages,
            system_message=system_prompt,
            sections=sections,
            budget_report=budget_report,
            source_summary=[
                *_build_source_summary(sections, budget_report),
                *_build_conversation_summary(context_messages),
            ],
            total_input_tokens=total_tokens,
            budget_enabled=self._assembler._calculate_budget(request) is not None,
            strategy_used=self._strategy.strategy_name,
            restored_context=restored,
        )

    def build(self, request: ContextBuildRequest) -> ContextBuildResult:
        """同步构建上下文。

        与 abuild 相同流程，但收集器使用同步调用。
        适用于无事件循环的场景。

        Args:
            request: 上下文构建请求。

        Returns:
            构建结果。
        """
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 在事件循环中，回退到同步策略
            return self._build_sync(request)

        return asyncio.run(self.abuild(request))

    def _build_sync(self, request: ContextBuildRequest) -> ContextBuildResult:
        """纯同步构建（不使用 asyncio.gather）。"""
        import asyncio

        # 使用单次 asyncio.run 调用 collect_all，内部使用 gather 并行执行
        try:
            sections = asyncio.run(self._coordinator.collect_all(request))
        except Exception:
            logger.debug("收集器执行失败", exc_info=True)
            sections = []

        # token 预算裁剪
        system_prompt, budget_report, total_tokens = self._assembler.assemble(
            sections, request
        )

        # 策略构建
        context_messages = self._strategy.build_context_messages(
            session_id=request.session_id,
            system_prompt=system_prompt,
        )

        final_messages: list[Any] = list(context_messages)
        if request.messages:
            final_messages.extend(request.messages)

        final_messages = self._micro_compact.compact(final_messages)

        return ContextBuildResult(
            messages=final_messages,
            system_message=system_prompt,
            sections=sections,
            budget_report=budget_report,
            source_summary=[
                *_build_source_summary(sections, budget_report),
                *_build_conversation_summary(context_messages),
            ],
            total_input_tokens=total_tokens,
            budget_enabled=self._assembler._calculate_budget(request) is not None,
            strategy_used=self._strategy.strategy_name,
        )

    async def _restore_context(self, session_id: str) -> Any:
        """从压缩摘要中恢复上下文。

        Args:
            session_id: 会话 ID。

        Returns:
            RestoredContext 实例，无摘要时返回 None。
        """
        try:
            strategy = self._strategy
            file_store = getattr(strategy, "_file_store", None)
            if not file_store:
                return None

            summary_data = file_store.read_summary(session_id)
            if not summary_data or not summary_data.get("summary"):
                return None

            return await self._restorer.restore(summary_data["summary"])  # type: ignore[union-attr]
        except Exception:
            logger.debug("上下文恢复失败", exc_info=True)
            return None

    def invalidate(self, name: str) -> None:
        """清除指定段的缓存。

        Args:
            name: 段名称（如 'memory'、'tools'）。
        """
        self._sections.invalidate(name)

    def invalidate_all(self) -> None:
        """清除全部段缓存（/clear、/compact 时调用）。"""
        self._sections.invalidate_all()

    @property
    def cached_section_names(self) -> list[str]:
        """当前已缓存的段名称列表。"""
        return self._sections.cached_names


def _build_source_summary(
    sections: list[Any],
    budget_report: list[ContextSourceBudget],
) -> list[ContextSourceSummary]:
    """从上下文段和预算报告构建来源摘要。"""
    budget_by_source = {row.source: row for row in budget_report}
    summaries: list[ContextSourceSummary] = []
    for section in sections:
        content = section.content or ""
        budget = budget_by_source.get(section.name)
        summaries.append(
            ContextSourceSummary(
                source=section.name,
                item_count=_estimate_item_count(content),
                token_count=budget.actual_tokens if budget else 0,
                truncated=bool(budget.truncated) if budget else False,
                cacheable=section.cacheable,
                summary=_summarize_section(content),
            )
        )
    return summaries


def _estimate_item_count(content: str) -> int:
    """估算来源包含的条目数量，避免暴露完整原文。"""
    if not content.strip():
        return 0
    bullet_count = sum(
        1
        for line in content.splitlines()
        if line.lstrip().startswith(("- ", "* ", "1. "))
    )
    return max(1, bullet_count)


def _summarize_section(content: str) -> str:
    """生成脱敏的一行来源摘要。"""
    for line in content.splitlines():
        normalized = line.strip()
        if normalized:
            return redact_for_audit(normalized, max_length=120)
    return ""


def _build_conversation_summary(messages: list[Any]) -> list[ContextSourceSummary]:
    """生成历史对话来源摘要。"""
    history_messages = [
        msg
        for msg in messages
        if getattr(msg, "type", "") not in {"system", "generic"}
    ]
    if not history_messages:
        return []

    content = "\n".join(str(getattr(msg, "content", "")) for msg in history_messages)
    return [
        ContextSourceSummary(
            source="conversation",
            item_count=len(history_messages),
            token_count=sum(len(str(getattr(msg, "content", ""))) // 4 for msg in history_messages),
            truncated=False,
            cacheable=False,
            summary=f"历史消息 {len(history_messages)} 条",
        )
    ]
