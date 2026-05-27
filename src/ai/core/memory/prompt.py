
"""记忆提示构建（合并原有 MemoryPromptBuilder 和 ContextPromptBuilder）。"""


import logging

from src.ai.core.prompts import PromptRenderRequest, prompt_service
from src.ai.exception.prompt_exception import PromptNotFoundError

from .types import MemorySearchResult

logger = logging.getLogger(__name__)


class MemoryPromptBuilder:
    """构建记忆相关的系统 prompt 片段。"""

    def build_system_context(self, memory_content: str, *, display_name: str = "Project") -> str:
        """构建系统 prompt 中的记忆部分。

        复用 DB 模板 memory.system_prompt，fallback 到内置默认。
        """
        try:
            result = prompt_service.render(
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
        except PromptNotFoundError:
            logger.warning("DB 中未找到 memory.system_prompt 模板，使用内置默认")
            return self._build_fallback(memory_content, display_name=display_name)

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
    def _build_fallback(memory_content: str, *, display_name: str = "Project") -> str:
        lines = [
            f"# {display_name} Memory",
            "",
            "记忆类型：",
            "- user：用户角色、目标、职责、偏好和稳定知识。",
            "- feedback：用户给出的工作指导、纠正和确认。",
            "- project：当前项目目标、正在进行的工作、bug 和事件。",
            "- reference：外部系统资源指针，例如 issue、文档或任务链接。",
            "",
            "使用规则：",
            "- 只使用和当前任务相关的记忆。",
            "- 不保存可从代码直接推导出的普通实现细节。",
            "- 不保存 API Key、token、密码或其他敏感信息。",
            "- 当记忆和当前用户指令冲突时，以当前用户指令为准。",
        ]
        if memory_content.strip():
            lines.extend(["", "## MEMORY.md", memory_content.strip()])
        return "\n".join(lines)
