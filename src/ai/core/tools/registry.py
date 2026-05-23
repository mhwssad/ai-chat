"""统一工具注册表。"""

from __future__ import annotations

from .errors import ToolNotFoundError
from .types import ToolDefinition


class ToolRegistry:
    """按工具名称管理工具定义。"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> ToolDefinition:
        self._tools[tool.name] = tool
        return tool

    def register_many(self, tools: list[ToolDefinition]) -> None:
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> ToolDefinition:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFoundError("工具不存在", context={"tool": name})
        return tool

    def list(self, *, enabled_only: bool = False) -> list[ToolDefinition]:
        tools = list(self._tools.values())
        if enabled_only:
            tools = [tool for tool in tools if tool.enabled]
        return sorted(tools, key=lambda item: (item.source_type, item.name))

    def clear(self) -> None:
        self._tools.clear()


tool_registry = ToolRegistry()

