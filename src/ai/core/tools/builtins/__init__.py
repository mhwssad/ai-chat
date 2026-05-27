"""内置工具包 — 导入各子模块触发自注册。"""

# 导入各工具模块以触发文件末尾的自注册
from . import file_tools, mcp_tools, placeholder_tools, search_tools, shell_tools, todo_tools

__all__ = [
    "file_tools",
    "mcp_tools",
    "placeholder_tools",
    "search_tools",
    "shell_tools",
    "todo_tools",
]
