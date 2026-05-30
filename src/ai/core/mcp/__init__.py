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


# 惰性导入：DI 容器单例
def __getattr__(name: str):
    if name == "mcp_manager":
        from src.ai.core.container import container

        return container.mcp_container.mcp_manager()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    "mcp_manager",
    "to_langchain_connections",
]
