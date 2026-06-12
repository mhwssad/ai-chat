"""会话管理路由 — 创建、列表、详情、归档、删除。"""

from typing import Annotated, Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query

from src.ai.api.schemas.common import MessageResponse
from src.ai.api.schemas.sessions import (
    SessionCreateRequest,
    SessionMessageResponse,
    SessionResponse,
)
from src.ai.core.container import AppContainer
from src.ai.service.session_service import SessionService

router = APIRouter()


@router.post("", response_model=SessionResponse, summary="创建会话", status_code=201)
@inject
async def create_session(
    req: SessionCreateRequest,
    svc: Annotated[
        SessionService, Depends(Provide[AppContainer.service_container.session_service])
    ],
) -> SessionResponse:
    """创建新会话。"""
    try:
        session = svc.create_session(
            session_id=req.session_id,
            title=req.title,
            current_model=req.current_model,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return SessionResponse(**session)


@router.get("", response_model=list[SessionResponse], summary="列出会话")
@inject
async def list_sessions(
    svc: Annotated[
        SessionService, Depends(Provide[AppContainer.service_container.session_service])
    ],
    status: str | None = Query(default="active", description="按状态过滤，默认 active"),
    limit: int = Query(default=100, ge=1, le=500, description="最大返回数量"),
) -> list[SessionResponse]:
    """列出会话。"""
    sessions = svc.list_sessions(status=status, limit=limit)
    return [SessionResponse(**s) for s in sessions]


@router.get("/{session_id}", response_model=SessionResponse, summary="获取会话")
@inject
async def get_session(
    session_id: str,
    svc: Annotated[
        SessionService, Depends(Provide[AppContainer.service_container.session_service])
    ],
) -> SessionResponse:
    """获取会话详情。"""
    session = svc.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
    return SessionResponse(**session)


@router.put("/{session_id}/archive", response_model=MessageResponse, summary="归档会话")
@inject
async def archive_session(
    session_id: str,
    svc: Annotated[
        SessionService, Depends(Provide[AppContainer.service_container.session_service])
    ],
) -> MessageResponse:
    """归档会话。"""
    archived = svc.archive_session(session_id)
    if not archived:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
    return MessageResponse(message=f"已归档: {session_id}")


@router.delete("/{session_id}", response_model=MessageResponse, summary="删除会话")
@inject
async def delete_session(
    session_id: str,
    svc: Annotated[
        SessionService, Depends(Provide[AppContainer.service_container.session_service])
    ],
) -> MessageResponse:
    """删除会话。"""
    deleted = svc.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
    return MessageResponse(message=f"已删除: {session_id}")


@router.get(
    "/{session_id}/messages",
    response_model=list[SessionMessageResponse],
    summary="获取会话消息历史",
)
@inject
async def get_session_messages(
    session_id: str,
    svc: Annotated[
        SessionService, Depends(Provide[AppContainer.service_container.session_service])
    ],
    history_manager: Annotated[
        Any,
        Depends(
            Provide[AppContainer.context_container.chat_history_manager]
        ),
    ],
) -> list[SessionMessageResponse]:
    """获取指定会话的所有对话消息，按时间顺序排列。"""
    session = svc.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

    messages = history_manager.get_messages(session_id)
    result: list[SessionMessageResponse] = []
    for msg in messages:
        role_map = {"human": "user", "ai": "assistant"}
        msg_type = getattr(msg, "type", "unknown")
        role = role_map.get(msg_type, msg_type)
        content = str(getattr(msg, "content", ""))
        result.append(SessionMessageResponse(role=role, content=content))

    return result
