"""对话路由 — 非流式、SSE 流式、OpenAI 兼容。"""


import json
from typing import Annotated, Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.ai.api.schemas.chat import (
    ChatRequest,
    ChatResponse,
    MessagesChatRequest,
    StreamChatRequest,
)
from src.ai.core.container import AppContainer
from src.ai.service.chat_service import ChatService
from src.ai.service.types import ChatOptions

router = APIRouter()


def _build_options(
    req: ChatRequest | StreamChatRequest | MessagesChatRequest,
    session_id: str,
    *,
    streaming: bool = False,
) -> ChatOptions:
    """从请求构建 ChatOptions。"""
    return ChatOptions(
        session_id=session_id,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        enable_memory=req.enable_memory,
        enable_tools=req.enable_tools,
        enable_rag=getattr(req, "enable_rag", False),
        enable_agent=getattr(req, "enable_agent", False),
        tools=getattr(req, "tools", None),
        streaming=streaming,
    )


@router.post("", response_model=ChatResponse, summary="非流式对话")
@inject
async def chat(
    req: ChatRequest,
    svc: Annotated[
        ChatService, Depends(Provide[AppContainer.service_container.chat_service])
    ],
) -> ChatResponse:
    """非流式对话（含完整工具循环）。"""
    opts = _build_options(req, req.session_id)
    result = await svc.chat(req.message, req.session_id, options=opts)
    return ChatResponse(
        content=result.content,
        session_id=result.session_id,
        tool_calls=result.tool_calls,
        iterations=result.iterations,
        error=result.error,
        usage=result.usage,
        context_sources=result.context_sources,
    )


@router.post("/stream", summary="SSE 流式对话")
@inject
async def chat_stream(
    req: StreamChatRequest,
    svc: Annotated[
        ChatService, Depends(Provide[AppContainer.service_container.chat_service])
    ],
) -> StreamingResponse:
    """SSE 流式对话。

    事件类型: token, tool_call, tool_result, done, error。
    """
    opts = _build_options(req, req.session_id, streaming=True)

    async def _event_generator() -> Any:
        async for event in svc.chat_stream(req.message, req.session_id, options=opts):
            event_type = event.get("event", "message")
            data = event.get("data", {})
            yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/messages", response_model=ChatResponse, summary="OpenAI 兼容对话")
@inject
async def chat_messages(
    req: MessagesChatRequest,
    svc: Annotated[
        ChatService, Depends(Provide[AppContainer.service_container.chat_service])
    ],
) -> ChatResponse:
    """OpenAI 兼容格式对话（接收 messages 数组）。"""
    opts = _build_options(req, req.session_id or "default")
    result = await svc.chat_with_messages(req.messages, req.session_id, options=opts)
    return ChatResponse(
        content=result.content,
        session_id=result.session_id,
        tool_calls=result.tool_calls,
        iterations=result.iterations,
        error=result.error,
        usage=result.usage,
        context_sources=result.context_sources,
    )
