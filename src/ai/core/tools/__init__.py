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


__all__ = [
    # 注册表
    "ToolRegistry",
    "register_tool",
    # 管理器
    "ToolManager",
    # 权限
    "PermissionChecker",
    "PermissionDecision",
    "PermissionLevel",
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
