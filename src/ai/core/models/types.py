"""通用模型请求和响应类型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ModelCapability = Literal["chat", "image", "audio", "video", "embedding"]
ChatRole = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True)
class ChatMessage:
    role: ChatRole
    content: str

    def to_api_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class ToolBinding:
    """可绑定工具声明，覆盖本地 tools、MCP tools 和 skills。"""

    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    source_type: str = "builtin"
    source_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelRequest:
    capability: ModelCapability
    model_id: int | None = None
    provider_key: str | None = None
    model_key: str | None = None
    session_id: str | None = None
    message_id: int | None = None
    tools: list[ToolBinding] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChatRequest(ModelRequest):
    messages: list[ChatMessage] = field(default_factory=list)
    temperature: float | None = None
    max_tokens: int | None = None

    def __init__(
        self,
        *,
        messages: list[ChatMessage],
        model_id: int | None = None,
        provider_key: str | None = None,
        model_key: str | None = None,
        session_id: str | None = None,
        message_id: int | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[ToolBinding] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        object.__setattr__(self, "capability", "chat")
        object.__setattr__(self, "model_id", model_id)
        object.__setattr__(self, "provider_key", provider_key)
        object.__setattr__(self, "model_key", model_key)
        object.__setattr__(self, "session_id", session_id)
        object.__setattr__(self, "message_id", message_id)
        object.__setattr__(self, "tools", tools or [])
        object.__setattr__(self, "metadata", metadata or {})
        object.__setattr__(self, "messages", messages)
        object.__setattr__(self, "temperature", temperature)
        object.__setattr__(self, "max_tokens", max_tokens)


@dataclass(frozen=True)
class EmbeddingRequest(ModelRequest):
    texts: list[str] = field(default_factory=list)

    def __init__(
        self,
        *,
        texts: list[str],
        model_id: int | None = None,
        provider_key: str | None = None,
        model_key: str | None = None,
        session_id: str | None = None,
        message_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        object.__setattr__(self, "capability", "embedding")
        object.__setattr__(self, "model_id", model_id)
        object.__setattr__(self, "provider_key", provider_key)
        object.__setattr__(self, "model_key", model_key)
        object.__setattr__(self, "session_id", session_id)
        object.__setattr__(self, "message_id", message_id)
        object.__setattr__(self, "tools", [])
        object.__setattr__(self, "metadata", metadata or {})
        object.__setattr__(self, "texts", texts)


@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class ModelCost:
    input_cost: float | None = None
    output_cost: float | None = None
    total_cost: float | None = None
    currency: str | None = None


@dataclass(frozen=True)
class ModelResponse:
    content: Any
    provider: str
    model: str
    capability: ModelCapability
    usage: ModelUsage = field(default_factory=ModelUsage)
    cost: ModelCost = field(default_factory=ModelCost)
    request_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelStreamChunk:
    """模型流式响应片段。"""

    delta: str = ""
    provider: str = ""
    model: str = ""
    capability: ModelCapability = "chat"
    usage: ModelUsage | None = None
    request_id: str | None = None
    finish_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
