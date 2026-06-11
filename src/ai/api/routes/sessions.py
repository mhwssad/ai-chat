"""会话管理路由 — 列表、详情、归档、删除。"""

from __future__ import annotations

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query

from src.ai.api.schemas.common import MessageResponse
from src.ai.api.schemas.sessions import SessionResponse
from src.ai.core.container import AppContainer
from src.ai.service.session_service import SessionService

router = APIRouter()


@router.get("", response_model=list[SessionResponse], summary="列出会话")
@inject
async def list_sessions(
    svc: Annotated[
        SessionService, Depends(Provide[AppContainer.service_container.session_service])
    ],
    status: str | None = Query(default=None, description="按状态过滤"),
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
