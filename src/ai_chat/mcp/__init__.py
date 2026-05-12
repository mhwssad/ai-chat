"""MCP 集成模块 — 连接外部 MCP 服务器 + 暴露内置工具。"""

from .config import mcp_settings
from .client import mcp_client_manager
from .server import mcp_server_manager
from .menu import menu_mcp

__all__ = [
    "mcp_settings",
    "mcp_client_manager",
    "mcp_server_manager",
    "menu_mcp",
]
