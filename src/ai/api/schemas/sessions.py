"""会话相关响应 Schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SessionResponse(BaseModel):
    """会话信息。"""

    session_id: str = Field(description="会话 ID")
    title: str | None = Field(default=None, description="会话标题")
    current_model: str | None = Field(default=None, description="当前使用的模型")
    status: str = Field(default="active", description="会话状态")
    message_count: int = Field(default=0, description="消息数量")
    created_at: str = Field(description="创建时间")
    last_active_at: str = Field(description="最后活跃时间")
