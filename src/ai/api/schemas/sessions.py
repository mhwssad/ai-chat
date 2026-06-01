"""会话 Schema。"""

from typing import Any

from pydantic import BaseModel, Field


class SessionInfo(BaseModel):
    """会话信息。"""

    session_id: str = Field(description="会话 ID")
    message_count: int = Field(description="消息数量")
    created_at: str | None = Field(default=None, description="创建时间")
    last_active_at: str | None = Field(default=None, description="最后活跃时间")


class SessionHistoryResponse(BaseModel):
    """会话历史响应。"""

    session_id: str = Field(description="会话 ID")
    messages: list[dict[str, Any]] = Field(description="消息列表")
