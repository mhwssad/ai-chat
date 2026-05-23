"""聊天服务。"""

from __future__ import annotations

import json
from collections.abc import Iterator

from src.ai.api.schemas.chat import ChatCompletionRequest
from src.ai.core.models import ChatMessage, ChatRequest, ModelClient, ModelResponse
from src.ai.core.tools import tool_manager


class ChatService:
    def __init__(self) -> None:
        self._client = ModelClient()

    def complete(self, request: ChatCompletionRequest) -> ModelResponse:
        return self._client.chat(self._to_chat_request(request))

    def stream(self, request: ChatCompletionRequest) -> Iterator[str]:
        for chunk in self._client.chat_stream(self._to_chat_request(request)):
            payload = {
                "delta": chunk.delta,
                "provider": chunk.provider,
                "model": chunk.model,
                "request_id": chunk.request_id,
                "finish_reason": chunk.finish_reason,
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    def _to_chat_request(self, request: ChatCompletionRequest) -> ChatRequest:
        tools = tool_manager.list_tool_bindings() if request.bind_tools else []
        return ChatRequest(
            messages=[
                ChatMessage(role=message.role, content=message.content)
                for message in request.messages
            ],
            model_id=request.model_id,
            provider_key=request.provider_key,
            model_key=request.model_key,
            session_id=request.session_id,
            message_id=request.message_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            tools=tools,
            metadata=request.metadata,
        )

