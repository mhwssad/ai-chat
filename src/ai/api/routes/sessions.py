"""会话管理路由。"""

from fastapi import APIRouter

from src.ai.api.deps import ContextServiceDep
from src.ai.api.schemas.sessions import SessionHistoryResponse, SessionInfo
from src.ai.api.schemas.common import MessageResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionInfo])
async def list_sessions(context_service: ContextServiceDep):
    """列出所有会话。"""
    strategy = context_service.strategy

    # 获取会话列表
    sessions = strategy.list_sessions()

    return [
        SessionInfo(
            session_id=s["session_id"],
            message_count=s.get("message_count", 0),
            created_at=s.get("created_at"),
            last_active_at=s.get("last_active_at"),
        )
        for s in sessions
    ]


@router.get("/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: str,
    context_service: ContextServiceDep,
):
    """获取会话历史。

    Args:
        session_id: 会话 ID。
    """
    strategy = context_service.strategy

    # 获取消息历史
    messages = await strategy.aget_history(session_id)

    return SessionHistoryResponse(
        session_id=session_id,
        messages=[
            {
                "role": msg.type,
                "content": msg.content,
            }
            for msg in messages
        ],
    )


@router.delete("/{session_id}", response_model=MessageResponse)
async def clear_session(
    session_id: str,
    context_service: ContextServiceDep,
):
    """清空会话。

    Args:
        session_id: 会话 ID。
    """
    strategy = context_service.strategy

    # 清空会话历史
    await strategy.aclear(session_id)

    return MessageResponse(message=f"会话 {session_id} 已清空")
