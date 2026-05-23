"""MCP 模块异常类型。"""

from __future__ import annotations

from src.ai.exception.base_exception import BaseExceptions


class MCPError(BaseExceptions):
    """MCP 基础异常。"""


class MCPConnectionError(MCPError):
    """MCP server 连接失败。"""


class MCPProtocolError(MCPError):
    """MCP 协议交互失败。"""


class MCPToolDiscoveryError(MCPError):
    """MCP 工具发现失败。"""


class MCPToolCallError(MCPError):
    """MCP 工具调用失败。"""
