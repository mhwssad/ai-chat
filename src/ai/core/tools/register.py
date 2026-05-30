"""全局工具注册机制 — 活跃注册表管理与便捷注册函数。"""

from collections.abc import Callable
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from src.ai.core.tools.registry import ToolMeta, ToolRegistry

# 当前活跃的注册表，由 load_builtin_tools() 设置
_active_registry: ToolRegistry | None = None


def _set_active_registry(registry: ToolRegistry) -> None:
    """设置当前活跃的注册表（供 load_builtin_tools 内部使用）。"""
    global _active_registry
    _active_registry = registry


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
    """注册工具到当前活跃的注册表。

    由 load_builtin_tools() 设置活跃注册表后，builtins 模块导入时自动调用此函数。
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

    registry = _active_registry
    if registry is None:
        raise RuntimeError(
            "register_tool() 在 load_builtin_tools() 之外被调用，无活跃注册表"
        )
    registry.register(tool_obj, meta=meta)
    return tool_obj
