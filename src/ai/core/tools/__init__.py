"""统一工具层。

Agent、模型绑定和 MCP 都应通过这里访问工具能力。
工具使用 langchain 原生 @tool 装饰器定义，自注册到 ToolRegistry。
"""

from src.ai.exception.tool_exception import (
    ToolDisabledError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionError,
)
from src.ai.core.tools.manager import ToolManager
from src.ai.core.tools.permissions import (
    PermissionChecker,
    PermissionDecision,
    PermissionLevel,
)
from src.ai.core.tools.register import register_tool
from src.ai.core.tools.registry import ToolRegistry
from src.ai.core.tools.types import ToolPlugin, ToolSourceType


# 惰性导入：DI 容器单例
def __getattr__(name: str):
    if name == "tool_registry":
        from src.ai.core.container import container

        return container.tool_container.tool_registry()
    if name == "tool_manager":
        from src.ai.core.container import container

        return container.tool_container.tool_manager()
    if name == "permission_checker":
        from src.ai.core.container import container

        return container.tool_container.permission_checker()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # 注册表
    "ToolRegistry",
    "register_tool",
    "tool_registry",
    # 管理器
    "ToolManager",
    "tool_manager",
    # 权限
    "PermissionChecker",
    "PermissionDecision",
    "PermissionLevel",
    "permission_checker",
    # 类型
    "ToolPlugin",
    "ToolSourceType",
    # 异常
    "ToolDisabledError",
    "ToolError",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolPermissionError",
]
