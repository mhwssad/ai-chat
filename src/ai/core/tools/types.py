"""统一工具类型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Literal

ToolSourceType = Literal["builtin", "mcp", "skill"]
ToolStatus = Literal["registered", "enabled", "disabled", "unavailable"]

ToolHandler = Callable[["ToolCallRequest"], Awaitable["ToolCallResult"]]


@dataclass(frozen=True)
class ToolDefinition:
    """统一工具声明。"""

    name: str
    description: str
    source_type: ToolSourceType = "builtin"
    source_id: str | None = None
    display_name: str | None = None
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] | None = None
    permissions: list[str] = field(default_factory=list)
    enabled: bool = True
    async_supported: bool = True
    timeout_seconds: float | None = None
    status: ToolStatus = "enabled"
    metadata: dict[str, Any] = field(default_factory=dict)
    handler: ToolHandler | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class ToolCallRequest:
    """统一工具调用请求。"""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None
    message_id: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolCallResult:
    """统一工具调用结果。"""

    tool_name: str
    content: Any
    structured_content: dict[str, Any] | None = None
    is_error: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

