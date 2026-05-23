"""聊天路由。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.ai.api.schemas.chat import ChatCompletionRequest, ChatCompletionResponse
from src.ai.api.services.chat_service import ChatService

router = APIRouter()


@router.post("/completions", response_model=ChatCompletionResponse)
async def create_completion(payload: ChatCompletionRequest):
    response = ChatService().complete(payload)
    return ChatCompletionResponse(
        content=response.content,
        provider=response.provider,
        model=response.model,
        request_id=response.request_id,
        usage={
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.total_tokens,
        },
        cost={
            "input_cost": response.cost.input_cost,
            "output_cost": response.cost.output_cost,
            "total_cost": response.cost.total_cost,
            "currency": response.cost.currency,
        },
    )


@router.post("/completions/stream")
async def create_completion_stream(payload: ChatCompletionRequest):
    return StreamingResponse(ChatService().stream(payload), media_type="text/event-stream")

