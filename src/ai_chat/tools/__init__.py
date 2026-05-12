"""工具包 — 自动发现并注册所有工具。"""

from .registry import tool_registry, registered_tool
from .menu import menu_tools

# 自动扫描当前包下所有模块，触发 @registered_tool 装饰器注册
tool_registry.scan(__name__)

__all__ = [
    "tool_registry",
    "registered_tool",
    "menu_tools",
]
