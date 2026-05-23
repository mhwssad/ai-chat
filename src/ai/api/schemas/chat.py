"""聊天 API schema。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ChatCompletionRequest(BaseModel):
    messages: list[ChatMessageIn]
    model_id: int | None = None
    provider_key: str | None = None
    model_key: str | None = None
    session_id: str | None = None
    message_id: int | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    bind_tools: bool = Field(default=False, description="是否绑定当前启用工具")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatCompletionResponse(BaseModel):
    content: Any
    provider: str
    model: str
    request_id: str | None = None
    usage: dict[str, int | None]
    cost: dict[str, float | str | None]

