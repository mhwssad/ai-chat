"""通用 Schema 定义。"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """错误响应。"""

    error: str = Field(description="错误消息")
    error_code: str | None = Field(default=None, description="错误代码")
    context: dict[str, Any] = Field(default_factory=dict, description="上下文信息")


class MessageResponse(BaseModel):
    """简单消息响应。"""

    message: str = Field(description="消息内容")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应。"""

    items: list[T] = Field(description="数据列表")
    total: int = Field(description="总数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页数量")
