"""对话路由。"""

import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.ai.api.deps import ChatServiceDep
from src.ai.api.schemas.chat import ChatRequest, ChatResponse
from src.ai.service.types import ChatOptions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: ChatServiceDep,
):
    """非流式对话。

    发送消息并获取完整的响应（含工具调用循环）。
    """
    messages = [msg.model_dump() for msg in request.messages]
    options = ChatOptions(
        session_id=request.session_id,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        tools=request.tools,
    )

    result = await service.chat_with_messages(
        messages=messages,
        session_id=request.session_id,
        options=options,
    )

    return ChatResponse(
        content=result.content,
        session_id=result.session_id,
        tool_calls=result.tool_calls,
        usage=result.usage,
        context_sources=result.context_sources,
    )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    service: ChatServiceDep,
):
    """流式对话（SSE）。

    发送消息并获取流式响应（含工具调用循环）。
    """
    # 提取最后一条用户消息
    user_input = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_input = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    options = ChatOptions(
        session_id=request.session_id,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        tools=request.tools,
        streaming=True,
    )

    async def event_generator():
        try:
            async for event in service.chat_stream(
                user_input=user_input,
                session_id=request.session_id or "",
                options=options,
            ):
                yield f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error("SSE 流式响应异常: %s", e, exc_info=True)
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
