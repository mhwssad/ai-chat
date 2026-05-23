"""MCP 模块通用类型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class MCPTool:
    """发现到的 MCP 工具元数据。"""

    server_key: str
    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] | None = None
    permission_policy: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def binding_name(self) -> str:
        """用于统一工具层的稳定名称。"""
        return f"{self.server_key}.{self.name}"


@dataclass(frozen=True)
class MCPCallResult:
    """MCP 工具调用结果。"""

    server_key: str
    tool_name: str
    content: Any
    structured_content: dict[str, Any] | None = None
    is_error: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MCPHealthResult:
    """MCP server 健康检查结果。"""

    server_key: str
    status: Literal["available", "unavailable", "error"]
    message: str = ""
    tool_count: int | None = None
