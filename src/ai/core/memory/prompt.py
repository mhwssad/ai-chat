"""记忆提示构建。"""

from __future__ import annotations

from pathlib import Path

from .scanner import MemoryScanner


class MemoryPromptBuilder:
    """构建可注入模型的记忆提示。"""

    def __init__(self, scanner: MemoryScanner | None = None) -> None:
        self._scanner = scanner or MemoryScanner()

    def build(
        self,
        *,
        display_name: str,
        memory_dir: str | Path,
        extra_guidelines: list[str] | None = None,
    ) -> str:
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
        if extra_guidelines:
            lines.extend(["", "额外规则：", *[f"- {item}" for item in extra_guidelines]])
        entrypoint = self._scanner.read_entrypoint(memory_dir)
        if entrypoint:
            lines.extend(["", "## MEMORY.md", entrypoint.strip()])
        return "\n".join(lines).strip()

