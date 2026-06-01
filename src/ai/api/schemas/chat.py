"""对话 Schema。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ContentBlock(BaseModel):
    """多模态内容块。

    支持文本和图像两种类型。
    """

    type: Literal["text", "image_url"] = Field(description="内容类型")
    text: str | None = Field(default=None, description="文本内容（type=text 时）")
    image_url: dict[str, str] | None = Field(
        default=None,
        description="图像 URL（type=image_url 时，格式: {url: string}）",
    )


class ChatMessage(BaseModel):
    """对话消息。

    content 可以是纯文本字符串或多模态内容块列表。
    """

    role: str = Field(description="角色（user/assistant/system）")
    content: str | list[ContentBlock] = Field(description="消息内容（纯文本或多模态）")


class ChatRequest(BaseModel):
    """对话请求。"""

    messages: list[ChatMessage] = Field(description="消息列表")
    session_id: str | None = Field(default=None, description="会话 ID")
    temperature: float | None = Field(default=None, description="温度参数")
    max_tokens: int | None = Field(default=None, description="最大输出 token 数")
    tools: list[str] | None = Field(
        default=None, description="可用工具列表（None 表示全部）"
    )


class ChatResponse(BaseModel):
    """对话响应。"""

    content: str = Field(description="响应内容")
    session_id: str = Field(description="会话 ID")
    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list, description="工具调用列表"
    )
    usage: dict[str, int] = Field(default_factory=dict, description="token 使用量")


class StreamEvent(BaseModel):
    """SSE 流式事件。"""

    event: str = Field(
        description="事件类型（token/tool_call/tool_progress/error/done）"
    )
    data: dict[str, Any] = Field(description="事件数据")
