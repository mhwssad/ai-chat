"""统一工具注册表。"""

from collections.abc import Callable
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from src.ai.exception.tool_exception import ToolNotFoundError


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
    """按工具名称管理 BaseTool 实例。"""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._meta: dict[str, ToolMeta] = {}

    def register(self, tool: BaseTool, *, meta: ToolMeta | None = None) -> BaseTool:
        self._tools[tool.name] = tool
        if meta is not None:
            self._meta[tool.name] = meta
        elif tool.name not in self._meta:
            self._meta[tool.name] = ToolMeta()
        return tool

    def register_many(self, tools: list[BaseTool]) -> None:
        for tool in tools:
            self.register(tool)

    def get_meta(self, name: str) -> ToolMeta:
        return self._meta.get(name, ToolMeta())

    def get(self, name: str) -> BaseTool:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFoundError("工具不存在", context={"tool": name})
        return tool

    def list(self, *, enabled_only: bool = False) -> list[BaseTool]:
        tools = list(self._tools.values())
        if enabled_only:
            tools = [t for t in tools if self._meta.get(t.name, ToolMeta()).enabled]
        return sorted(tools, key=lambda t: (self._meta.get(t.name, ToolMeta()).source_type, t.name))

    def clear(self) -> None:
        self._tools.clear()
        self._meta.clear()


tool_registry = ToolRegistry()


def register_tool(
    func: Callable[..., Any] | BaseTool,
    *,
    name: str | None = None,
    description: str | None = None,
    source_type: str = "builtin",
    source_id: str | None = None,
    permissions: list[str] | None = None,
    essential: bool = False,
    enabled: bool = True,
) -> BaseTool:
    """注册工具到全局注册表。

    支持两种方式：
    1. 传入 @tool 装饰的 BaseTool 实例（直接注册）
    2. 传入普通 async 函数（用 StructuredTool.from_function() 包装后注册）

    附加 source_type、permissions、essential 等元数据属性到工具实例。
    """
    if isinstance(func, BaseTool):
        tool_obj = func
    else:
        tool_obj = StructuredTool.from_function(
            coroutine=func,
            name=name,
            description=description,
        )

    meta = ToolMeta(
        source_type=source_type,
        source_id=source_id,
        permissions=permissions or [],
        essential=essential,
        enabled=enabled,
    )
    tool_registry.register(tool_obj, meta=meta)
    return tool_obj
