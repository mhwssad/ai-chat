"""MCP 核心能力。

该模块负责从 JSON 文件读取 MCP server 配置、发现工具、调用工具。
使用 langchain-mcp-adapters 与 langchain 生态兼容。
"""

from src.ai.exception.mcp_config_exception import MCPConfigError
from src.ai.exception.mcp_exception import (
    MCPConnectionError,
    MCPError,
    MCPProtocolError,
    MCPToolCallError,
    MCPToolDiscoveryError,
)

from .config import MCPConfigRepository
from .manager import MCPManager, mcp_manager
from .types import MCPServerConfig, MCPHealthResult

__all__ = [
    "MCPConfigError",
    "MCPConfigRepository",
    "MCPConnectionError",
    "MCPError",
    "MCPHealthResult",
    "MCPManager",
    "MCPProtocolError",
    "MCPServerConfig",
    "MCPToolCallError",
    "MCPToolDiscoveryError",
    "mcp_manager",
]
