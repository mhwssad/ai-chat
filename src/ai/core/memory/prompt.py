"""记忆提示构建 — 构建系统 prompt 片段和格式化工具。"""

from __future__ import annotations

from src.ai.config.logging_setup import get_logger
from typing import TYPE_CHECKING, Any

from src.ai.core.prompts import PromptRenderRequest

from .types import MemorySearchResult

if TYPE_CHECKING:
    from src.ai.core.prompts.service import PromptService

logger = get_logger(__name__)


class MemoryPromptBuilder:
    """构建记忆相关的系统 prompt 片段。

    Args:
        prompt_service: 提示词服务（从 DB 获取提示词模板）。
    """

    def __init__(self, prompt_service: PromptService) -> None:
        self._prompt_service = prompt_service

    def build_system_context(
        self, memory_content: str, *, display_name: str = "Project"
    ) -> str:
        """构建系统 prompt 中的记忆部分。

        从 DB 模板 memory.system_prompt 渲染。
        """
        result = self._prompt_service.render(  # type: ignore[attr-defined]
            PromptRenderRequest(
                prompt_key="memory.system_prompt",
                variables={
                    "display_name": display_name,
                    "extra_guidelines": [],
                    "entrypoint": memory_content,
                },
            )
        )
        return result.content

    def build_injection(self, results: list[MemorySearchResult]) -> str:
        """构建注入到对话中的相关记忆片段。"""
        if not results:
            return ""

        lines = ["## 相关记忆", ""]
        for result in results:
            lines.append(f"- [{result.entry.memory_type}] {result.entry.description}")
            if result.entry.content:
                lines.append(f"  {result.entry.content[:200]}")
        return "\n".join(lines)

    @staticmethod
    def format_file_references(
        file_refs: list[dict[str, Any]], max_show: int = 20
    ) -> str:
        """格式化文件引用提示。

        将压缩摘要中的文件引用格式化为可读列表，
        用于注入系统 prompt，帮助模型了解可回读的原始消息位置。

        Args:
            file_refs: 文件引用列表（含 index、snippet 字段）。
            max_show: 最多显示的引用数。

        Returns:
            格式化的引用文本。
        """
        if not file_refs:
            return ""
        lines = ["### 可回读的原始消息位置", ""]
        for ref in file_refs[:max_show]:
            idx = ref.get("index", "?")
            snippet = str(ref.get("snippet", ""))[:50]
            lines.append(f"- 消息#{idx}: {snippet}")
        return "\n".join(lines)
