"""MCP 模块通用类型。"""

from dataclasses import dataclass, field
from typing import Any, Literal

MCPTransport = Literal["stdio", "http", "sse", "websocket"]


@dataclass(frozen=True)
class MCPServerConfig:
    """MCP server 运行时配置。"""

    server_key: str
    transport: MCPTransport
    display_name: str | None = None
    command: str | None = None
    args: list[str] = field(default_factory=list)
    url: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    permission_policy: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MCPHealthResult:
    """MCP server 健康检查结果。"""

    server_key: str
    status: Literal["not_configured", "configured", "unavailable", "available", "error"]
    message: str = ""
    tool_count: int | None = None
