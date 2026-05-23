"""MCP API schema。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MCPServerResponse(BaseModel):
    server_key: str
    transport: str
    display_name: str | None = None
    enabled: bool
    metadata: dict[str, Any] = Field(default_factory=dict)


class MCPToolResponse(BaseModel):
    server_key: str
    name: str
    binding_name: str
    description: str
    input_schema: dict[str, Any]

