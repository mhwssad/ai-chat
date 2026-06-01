"""统一工具注册表 — 工具数据存储与查询。"""

from __future__ import annotations

import logging

from langchain_core.tools import BaseTool

from src.ai.exception.tool_exception import ToolNotFoundError

logger = logging.getLogger(__name__)


class ToolMeta:
    """工具元数据（Pydantic BaseTool 不支持动态属性）。"""

    __slots__ = ("source_type", "source_id", "permissions", "essential", "enabled")

    def __init__(
        self,
        source_type: str = "builtin",
        source_id: str | None = None,
        permissions: list[str] | None = None,
        essential: bool = False,
        enabled: bool = True,
    ) -> None:
        self.source_type = source_type
        self.source_id = source_id
        self.permissions = permissions or []
        self.essential = essential
        self.enabled = enabled


class ToolRegistry:
    """按工具名称管理 BaseTool 实例。

    职责：工具数据存储、按名称检索、列表查询、关键词搜索。
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._meta: dict[str, ToolMeta] = {}

    # ── 存储 ────────────────────────────────────────────────

    def register(self, tool: BaseTool, *, meta: ToolMeta | None = None) -> BaseTool:
        """注册工具。同名工具覆盖时记录 warning 日志。"""
        if tool.name in self._tools:
            existing_source = self._meta.get(tool.name, ToolMeta()).source_type
            new_source = meta.source_type if meta else "builtin"
            logger.warning(
                "工具名称冲突，覆盖已有工具: name=%s, existing_source=%s, new_source=%s",
                tool.name,
                existing_source,
                new_source,
            )
        self._tools[tool.name] = tool
        if meta is not None:
            self._meta[tool.name] = meta
        elif tool.name not in self._meta:
            self._meta[tool.name] = ToolMeta()
        return tool

    def register_many(self, tools: list[BaseTool]) -> None:
        """批量注册工具。"""
        for tool in tools:
            self.register(tool)

    def clear(self) -> None:
        """清空注册表。"""
        self._tools.clear()
        self._meta.clear()

    # ── 检索 ────────────────────────────────────────────────

    def get(self, name: str) -> BaseTool:
        """按名称获取工具，不存在则抛出 ToolNotFoundError。"""
        tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFoundError("工具不存在", context={"tool": name})
        return tool

    def get_meta(self, name: str) -> ToolMeta:
        """按名称获取工具元数据。"""
        return self._meta.get(name, ToolMeta())

    # ── 查询 ────────────────────────────────────────────────

    def list(self, *, enabled_only: bool = False) -> list[BaseTool]:
        """列出已注册工具（按 source_type + name 排序）。"""
        tools = list(self._tools.values())
        if enabled_only:
            tools = [t for t in tools if self._meta.get(t.name, ToolMeta()).enabled]
        return sorted(
            tools,
            key=lambda t: (self._meta.get(t.name, ToolMeta()).source_type, t.name),
        )

    def search(self, query: str, *, enabled_only: bool = True) -> list[BaseTool]:
        """按关键词搜索工具（匹配 name 或 description）。"""
        q = query.lower()
        return [
            t
            for t in self.list(enabled_only=enabled_only)
            if q in t.name.lower() or q in (t.description or "").lower()
        ]
