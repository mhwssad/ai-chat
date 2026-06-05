"""统一工具注册表 — 工具数据存储与查询。"""

from __future__ import annotations

import builtins
import logging

from langchain_core.tools import BaseTool

from src.ai.exception.tool_exception import ToolNotFoundError
from src.ai.core.tools.types import ToolDescriptor, ToolMeta

logger = logging.getLogger(__name__)


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

    def get_descriptor(self, name: str) -> ToolDescriptor:
        """按名称获取统一工具描述对象。"""
        tool = self.get(name)
        return ToolDescriptor.from_tool(tool, self.get_meta(name))

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

    def search(
        self, query: str, *, enabled_only: bool = True
    ) -> builtins.list[BaseTool]:
        """按关键词搜索工具（匹配 name 或 description）。"""
        q = query.lower()
        registered = self.list(enabled_only=enabled_only)
        return [
            t
            for t in registered
            if q in t.name.lower() or q in (t.description or "").lower()
        ]

    def list_descriptors(self, *, enabled_only: bool = False) -> list[ToolDescriptor]:
        """列出统一工具描述对象。"""
        return [
            ToolDescriptor.from_tool(tool, self.get_meta(tool.name))
            for tool in self.list(enabled_only=enabled_only)
        ]
