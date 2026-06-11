"""通用请求/响应 Schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    """操作结果消息。"""

    message: str = Field(description="操作结果消息")
