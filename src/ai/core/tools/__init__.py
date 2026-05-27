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
from src.ai.core.tools.manager import ToolManager, tool_manager
from src.ai.core.tools.registry import ToolRegistry, register_tool, tool_registry
from src.ai.core.tools.types import ToolFilterContext, ToolSourceType

__all__ = [
    # 注册表
    "ToolRegistry",
    "register_tool",
    "tool_registry",
    # 管理器
    "ToolManager",
    "tool_manager",
    # 类型
    "ToolFilterContext",
    "ToolSourceType",
    # 异常
    "ToolDisabledError",
    "ToolError",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolPermissionError",
]
