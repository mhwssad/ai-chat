"""对话路由。"""

import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.ai.api.deps import ContextServiceDep, ModelServiceDep, ToolManagerDep
from src.ai.api.schemas.chat import ChatRequest, ChatResponse
from src.ai.api.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_chat_service(
    model_service: ModelServiceDep,
    context_service: ContextServiceDep,
    tool_manager: ToolManagerDep,
) -> ChatService:
    """创建 ChatService 实例。"""
    return ChatService(
        model_service=model_service,
        context_service=context_service,
        tool_manager=tool_manager,
    )


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    model_service: ModelServiceDep,
    context_service: ContextServiceDep,
    tool_manager: ToolManagerDep,
):
    """非流式对话。

    发送消息并获取完整的响应。
    """
    service = _get_chat_service(model_service, context_service, tool_manager)

    messages = [msg.model_dump() for msg in request.messages]
    result = await service.chat(
        messages=messages,
        session_id=request.session_id,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        tools=request.tools,
    )

    return ChatResponse(
        content=result["content"],
        session_id=result["session_id"],
        tool_calls=result["tool_calls"],
        usage=result["usage"],
    )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    model_service: ModelServiceDep,
    context_service: ContextServiceDep,
    tool_manager: ToolManagerDep,
):
    """流式对话（SSE）。

    发送消息并获取流式响应。
    """
    service = _get_chat_service(model_service, context_service, tool_manager)

    messages = [msg.model_dump() for msg in request.messages]

    async def event_generator():
        try:
            async for event in service.chat_stream(
                messages=messages,
                session_id=request.session_id,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=request.tools,
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
