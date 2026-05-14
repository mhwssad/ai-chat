"""工具包 — 自动加载系统工具，其他工具按名称懒加载。"""

from .registry import ToolType, tool_registry, registered_tool
from .menu import menu_tools

# 仅自动加载系统工具，非系统工具在按名称解析时搜索加载
tool_registry.load_system_tools()

__all__ = [
    "ToolType",
    "tool_registry",
    "registered_tool",
    "menu_tools",
]
