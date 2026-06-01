"""工具描述收集器 — 收集已启用工具的描述信息。"""

import logging
from typing import TYPE_CHECKING

from src.ai.core.context.collector import ContextCollector
from src.ai.core.context.types import (
    ContextBuildRequest,
    ContextCollectorResult,
    ContextSection,
)

if TYPE_CHECKING:
    from src.ai.core.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolCollector(ContextCollector):
    """收集工具描述上下文。

    列出已启用的内置工具和 MCP 工具名称。
    可缓存（工具列表变化不频繁）。

    Args:
        tool_registry: 工具注册表实例。
    """

    def __init__(self, tool_registry: "ToolRegistry") -> None:
        self._registry = tool_registry

    @property
    def name(self) -> str:
        return "tools"

    async def collect(self, request: ContextBuildRequest) -> ContextCollectorResult:
        if not request.enable_tools:
            return ContextCollectorResult()

        try:
            tools = self._registry.list(enabled_only=True)
            if not tools:
                return ContextCollectorResult()

            grouped: dict[str, list[str]] = {"builtin": [], "mcp": [], "skill": []}
            for tool in tools:
                meta = self._registry.get_meta(tool.name)
                source = meta.source_type if meta.source_type in grouped else "builtin"
                grouped[source].append(tool.name)

            lines = ["## 工具使用指引", ""]
            if grouped["builtin"]:
                lines.append(f"内置工具: {', '.join(grouped['builtin'])}")
            if grouped["mcp"]:
                lines.append(f"MCP 工具: {', '.join(grouped['mcp'])}")
            if grouped["skill"]:
                lines.append(f"技能工具: {', '.join(grouped['skill'])}")
            lines.extend(
                [
                    "",
                    "使用原则:",
                    "- 需要读取文件、搜索代码、执行命令时，优先调用对应工具",
                    "- 多步骤任务可以连续调用多个工具",
                    "- 工具调用失败时分析原因，不要直接放弃",
                ]
            )

            section = ContextSection(
                name="tools",
                content="\n".join(lines),
                priority=3,
                cacheable=True,
            )
            return ContextCollectorResult(sections=[section])
        except Exception:
            logger.debug("工具描述收集失败", exc_info=True)
            return ContextCollectorResult()
