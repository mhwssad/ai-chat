"""上下文组装器 — token 预算分配和裁剪。"""

import logging

from src.ai.core.context.types import (
    ContextBuildRequest,
    ContextSection,
    ContextSourceBudget,
)
from src.ai.utils.token_utils import token_counter
from src.ai.config.model_settings import ChatModelConfig

logger = logging.getLogger(__name__)

# 缓存边界标记
CACHE_BOUNDARY_STATIC = "__SYSTEM_PROMPT_STATIC_END__"
CACHE_BOUNDARY_DYNAMIC = "__SYSTEM_PROMPT_DYNAMIC_START__"


class ContextAssembler:
    """上下文组装器。

    按优先级分配 token 预算，从低优先级开始裁剪。
    裁剪顺序：RAG(4) > 工具(3) > 记忆(2) > 系统提示(0)。
    """

    def __init__(self, settings: ChatModelConfig) -> None:
        self._settings = settings

    def assemble(
        self,
        sections: list[ContextSection],
        request: ContextBuildRequest,
    ) -> tuple[str, list[ContextSourceBudget], int]:
        """组装系统提示，执行 token 预算。

        Args:
            sections: 按 priority 排序的上下文段列表。
            request: 上下文构建请求（含 model_config 和 safety_margin）。

        Returns:
            (system_prompt, budget_report, total_tokens)
        """
        if not sections:
            return "", [], 0

        budget = self._calculate_budget(request)
        if budget is None:
            # 无预算限制，直接合并（带缓存边界）
            static_sections = [s for s in sections if s.cacheable and s.content]
            dynamic_sections = [s for s in sections if not s.cacheable and s.content]

            parts: list[str] = []
            if static_sections:
                parts.extend(s.content for s in static_sections)
                parts.append(CACHE_BOUNDARY_STATIC)
            if dynamic_sections:
                parts.append(CACHE_BOUNDARY_DYNAMIC)
                parts.extend(s.content for s in dynamic_sections)

            total = sum(token_counter.count_text_tokens(s.content) for s in sections)
            report = [
                ContextSourceBudget(
                    source=s.name,
                    actual_tokens=token_counter.count_text_tokens(s.content),
                )
                for s in sections
            ]
            return "\n\n".join(parts), report, total

        # 有预算限制，执行裁剪
        return self._fit_to_budget(sections, budget)

    def _calculate_budget(self, request: ContextBuildRequest) -> int | None:
        """计算 token 预算。"""
        config = request.model_config
        context_window = getattr(config, "context_window", None) if config else None
        max_output = getattr(config, "max_output_tokens", None) if config else None
        context_window = context_window or self._settings.context_window
        max_output = max_output or self._settings.max_output_tokens
        if context_window:
            return max(context_window - max_output - request.safety_margin, 0)
        return None

    def _fit_to_budget(
        self,
        sections: list[ContextSection],
        budget: int,
    ) -> tuple[str, list[ContextSourceBudget], int]:
        """将段列表拟合到 token 预算内。

        从最低优先级（数值最大）开始裁剪。
        """
        section_tokens = [
            (s, token_counter.count_text_tokens(s.content)) for s in sections
        ]
        total = sum(t for _, t in section_tokens)

        report = [
            ContextSourceBudget(source=s.name, actual_tokens=t)
            for s, t in section_tokens
        ]

        if total <= budget:
            static_sections = [s for s in sections if s.cacheable and s.content]
            dynamic_sections = [s for s in sections if not s.cacheable and s.content]
            parts: list[str] = []
            if static_sections:
                parts.extend(s.content for s in static_sections)
                parts.append(CACHE_BOUNDARY_STATIC)
            if dynamic_sections:
                parts.append(CACHE_BOUNDARY_DYNAMIC)
                parts.extend(s.content for s in dynamic_sections)
            return "\n\n".join(parts), report, total

        # 从低优先级（数值大）到高优先级（数值小）裁剪
        sorted_pairs = sorted(section_tokens, key=lambda x: -x[0].priority)

        remaining_budget = budget
        kept: list[tuple[ContextSection, int]] = []

        # 第一轮：高优先级段直接保留
        for section, tokens in reversed(sorted_pairs):
            if remaining_budget >= tokens:
                kept.append((section, tokens))
                remaining_budget -= tokens

        # 第二轮：低优先级段尝试裁剪后保留
        for section, tokens in sorted_pairs:
            if any(s.name == section.name for s, _ in kept):
                continue
            if remaining_budget <= 0:
                for r in report:
                    if r.source == section.name:
                        r.truncated = True
                continue
            # 裁剪到剩余预算
            truncated_content = self._truncate_to_tokens(
                section.content, remaining_budget
            )
            truncated_tokens = token_counter.count_text_tokens(truncated_content)
            kept.append(
                (
                    ContextSection(
                        name=section.name,
                        content=truncated_content,
                        priority=section.priority,
                        cacheable=section.cacheable,
                    ),
                    truncated_tokens,
                )
            )
            for r in report:
                if r.source == section.name:
                    r.truncated = True
            remaining_budget -= truncated_tokens

        # 按 priority 排序输出，带缓存边界
        kept.sort(key=lambda x: x[0].priority)
        static_kept = [(s, t) for s, t in kept if s.cacheable and s.content]
        dynamic_kept = [(s, t) for s, t in kept if not s.cacheable and s.content]

        parts = []
        if static_kept:
            parts.extend(s.content for s, _ in static_kept)
            parts.append(CACHE_BOUNDARY_STATIC)
        if dynamic_kept:
            parts.append(CACHE_BOUNDARY_DYNAMIC)
            parts.extend(s.content for s, _ in dynamic_kept)

        total_used = sum(t for _, t in kept)
        return "\n\n".join(parts), report, total_used

    @staticmethod
    def _truncate_to_tokens(text: str, max_tokens: int) -> str:
        """将文本截断到指定 token 数。

        使用 tiktoken 精确截断，逐步缩减直到 token 数达标。

        Args:
            text: 输入文本。
            max_tokens: 最大 token 数。

        Returns:
            截断后的文本。
        """
        if not text:
            return ""

        current_tokens = token_counter.count_text_tokens(text)
        if current_tokens <= max_tokens:
            return text

        # 按比例估算截断位置，然后微调
        ratio = max_tokens / current_tokens
        estimated_chars = int(len(text) * ratio * 0.95)  # 留 5% 余量
        truncated = text[:estimated_chars]

        # 微调：确保 token 数不超限
        while (
            token_counter.count_text_tokens(truncated) > max_tokens
            and estimated_chars > 0
        ):
            estimated_chars -= max(1, estimated_chars // 20)  # 每次缩减 5%
            truncated = text[:estimated_chars]

        return truncated + "\n...(已截断)"
