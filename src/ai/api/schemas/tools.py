"""工具 API schema。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolResponse(BaseModel):
    name: str
    description: str
    source_type: str
    source_id: str | None = None
    enabled: bool
    status: str
    permissions: list[str]
    input_schema: dict[str, Any]


class ToolCallRequestIn(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None
    message_id: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    tool_name: str
    content: Any
    structured_content: dict[str, Any] | None = None
    is_error: bool = False
    raw: dict[str, Any] = Field(default_factory=dict)

