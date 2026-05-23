"""统一工具层。

Agent、模型绑定和 MCP/Skills 都应通过这里访问工具能力。
"""

from src.ai.core.tools.adapters import tool_to_binding, tools_to_bindings
from src.ai.core.tools.builtins import get_builtin_tools, get_placeholder_tools
from src.ai.core.tools.errors import (
    ToolDisabledError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionError,
)
from src.ai.core.tools.executor import ToolExecutor, tool_executor
from src.ai.core.tools.manager import ToolManager, tool_manager
from src.ai.core.tools.registry import ToolRegistry, tool_registry
from src.ai.core.tools.types import (
    ToolCallRequest,
    ToolCallResult,
    ToolDefinition,
    ToolSourceType,
    ToolStatus,
)

__all__ = [
    "ToolCallRequest",
    "ToolCallResult",
    "ToolDefinition",
    "ToolDisabledError",
    "ToolError",
    "ToolExecutionError",
    "ToolExecutor",
    "ToolManager",
    "ToolNotFoundError",
    "ToolPermissionError",
    "ToolRegistry",
    "ToolSourceType",
    "ToolStatus",
    "get_builtin_tools",
    "get_placeholder_tools",
    "tool_executor",
    "tool_manager",
    "tool_registry",
    "tool_to_binding",
    "tools_to_bindings",
]

