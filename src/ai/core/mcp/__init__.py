"""MCP 核心能力。

该模块负责 MCP server 配置读取、客户端管理、工具发现和资源访问。
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

from .adapter import to_langchain_connections
from .client import MCPClient
from .config import MCPConfigRepository
from .manager import MCPManager
from .types import MCPServerConfig, MCPHealthResult


__all__ = [
    "MCPClient",
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
    "to_langchain_connections",
]
