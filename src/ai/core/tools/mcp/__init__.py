"""MCP 核心能力。

该模块负责从数据库读取 MCP server 配置、发现工具、调用工具，并把 MCP 工具
转换为模型层可绑定的 ToolBinding。
"""

from src.ai.core.tools.mcp.client import MCPClient
from src.ai.core.tools.mcp.errors import (
    MCPConnectionError,
    MCPError,
    MCPProtocolError,
    MCPToolCallError,
    MCPToolDiscoveryError,
)
from src.ai.core.tools.mcp.manager import MCPManager, mcp_manager
from src.ai.storage.mcp_repository import MCPConfigError, MCPConfigRepository, MCPServerConfig
from src.ai.core.tools.mcp.tool_adapter import mcp_tool_to_binding, mcp_tools_to_bindings
from src.ai.core.tools.mcp.types import (
    MCPCallResult,
    MCPHealthResult,
    MCPTool,
)

__all__ = [
    "MCPCallResult",
    "MCPClient",
    "MCPConfigError",
    "MCPConfigRepository",
    "MCPConnectionError",
    "MCPError",
    "MCPHealthResult",
    "MCPManager",
    "MCPProtocolError",
    "MCPServerConfig",
    "MCPTool",
    "MCPToolCallError",
    "MCPToolDiscoveryError",
    "mcp_manager",
    "mcp_tool_to_binding",
    "mcp_tools_to_bindings",
]
