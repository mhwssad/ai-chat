"""压缩后上下文恢复器 — 从压缩摘要中提取关键信息恢复为可注入的上下文。"""

from src.ai.config.logging_setup import get_logger
import re
from dataclasses import dataclass, field

logger = get_logger(__name__)


@dataclass(frozen=True)
class RestoredContext:
    """从压缩摘要中恢复的上下文信息。

    Attributes:
        plan: 当前计划/任务（从 Current Work 和 Next Step 章节提取）。
        pending_tasks: 待办任务列表（从 Pending Tasks and TODOs 章节提取）。
        key_files: 关键文件内容（预留接口，当前为空）。
    """

    plan: str = ""
    pending_tasks: list[str] = field(default_factory=list)
    key_files: list[str] = field(default_factory=list)

    def to_system_message(self) -> str:
        """将恢复的上下文格式化为可注入的系统消息。"""
        parts: list[str] = []

        if self.plan:
            parts.append(f"## 当前计划\n{self.plan}")

        if self.pending_tasks:
            task_lines = "\n".join(f"- {t}" for t in self.pending_tasks)
            parts.append(f"## 待办任务\n{task_lines}")

        if self.key_files:
            file_lines = "\n".join(f"- {f}" for f in self.key_files)
            parts.append(f"## 关键文件\n{file_lines}")

        return "\n\n".join(parts)


class ContextRestorer:
    """压缩后上下文恢复器。

    从 FullCompact 生成的 9 章节标准摘要中提取关键信息，
    恢复为可注入到新对话上下文中的结构化数据。
    """

    async def restore(self, summary: str) -> RestoredContext:
        """从压缩摘要中恢复上下文。

        Args:
            summary: FullCompact 生成的压缩摘要文本。

        Returns:
            恢复的上下文信息。
        """
        if not summary.strip():
            return RestoredContext()

        plan = self._extract_plan(summary)
        pending_tasks = self._extract_pending_tasks(summary)

        return RestoredContext(
            plan=plan,
            pending_tasks=pending_tasks,
        )

    @staticmethod
    def _extract_plan(summary: str) -> str:
        """从 Current Work 和 Next Step 章节提取当前计划。"""
        parts: list[str] = []

        # 提取 Current Work
        current_work = ContextRestorer._extract_section(summary, "Current Work")
        if current_work:
            parts.append(current_work)

        # 提取 Next Step
        next_step = ContextRestorer._extract_section(summary, "Next Step")
        if next_step:
            parts.append(next_step)

        return "\n\n".join(parts)

    @staticmethod
    def _extract_pending_tasks(summary: str) -> list[str]:
        """从 Pending Tasks and TODOs 章节提取待办列表。"""
        section = ContextRestorer._extract_section(summary, "Pending Tasks and TODOs")
        if not section:
            return []

        tasks: list[str] = []
        for line in section.split("\n"):
            line = line.strip()
            # 匹配 - 开头的列表项
            match = re.match(r"^[-*]\s+(.+)$", line)
            if match:
                task = match.group(1).strip()
                # 去除来源标注 [消息#N]
                task = re.sub(r"\s*\[消息#\d+\]\s*$", "", task)
                if task:
                    tasks.append(task)

        return tasks

    @staticmethod
    def _extract_section(summary: str, section_name: str) -> str:
        """从摘要中提取指定章节的内容。"""
        # 匹配 ## Section Name 后面的内容，直到下一个 ## 或文本结束
        pattern = rf"##\s+{re.escape(section_name)}\s*\n(.*?)(?=\n##\s|\Z)"
        match = re.search(pattern, summary, re.DOTALL)
        if match:
            content = match.group(1).strip()
            # 排除 "暂无" 等空内容标记
            if content and content not in ("暂无", "无", "N/A", "None"):
                return content
        return ""
