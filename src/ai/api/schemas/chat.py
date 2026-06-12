"""对话相关请求/响应 Schema。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """非流式对话请求。"""

    message: str = Field(..., min_length=1, description="用户输入文本")
    session_id: str = Field(default="default", description="会话 ID")
    temperature: float | None = Field(
        default=None, ge=0.0, le=2.0, description="温度参数"
    )
    max_tokens: int | None = Field(default=None, ge=1, description="最大 token 数")
    enable_memory: bool = Field(default=True, description="是否启用记忆")
    enable_tools: bool = Field(default=True, description="是否启用工具")
    enable_rag: bool = Field(default=False, description="是否启用 RAG")
    enable_agent: bool = Field(default=False, description="是否启用 Agent 自动执行")
    tools: list[str] | None = Field(default=None, description="工具白名单")


class ChatResponse(BaseModel):
    """非流式对话响应。"""

    content: str = Field(default="", description="回复内容")
    session_id: str = Field(default="", description="会话 ID")
    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list, description="工具调用记录"
    )
    iterations: int = Field(default=0, description="工具循环轮数")
    error: str | None = Field(default=None, description="错误信息")
    usage: dict[str, int] = Field(default_factory=dict, description="token 用量")
    context_sources: list[dict[str, Any]] = Field(
        default_factory=list, description="上下文来源摘要"
    )


class StreamChatRequest(BaseModel):
    """流式对话请求（字段与非流式一致）。"""

    message: str = Field(..., min_length=1, description="用户输入文本")
    session_id: str = Field(default="default", description="会话 ID")
    temperature: float | None = Field(
        default=None, ge=0.0, le=2.0, description="温度参数"
    )
    max_tokens: int | None = Field(default=None, ge=1, description="最大 token 数")
    enable_memory: bool = Field(default=True, description="是否启用记忆")
    enable_tools: bool = Field(default=True, description="是否启用工具")
    enable_rag: bool = Field(default=False, description="是否启用 RAG")
    enable_agent: bool = Field(default=False, description="是否启用 Agent 自动执行")
    tools: list[str] | None = Field(default=None, description="工具白名单")


class MessagesChatRequest(BaseModel):
    """OpenAI 兼容格式对话请求。"""

    messages: list[dict[str, Any]] = Field(..., min_length=1, description="消息列表")
    session_id: str | None = Field(default=None, description="会话 ID")
    temperature: float | None = Field(
        default=None, ge=0.0, le=2.0, description="温度参数"
    )
    max_tokens: int | None = Field(default=None, ge=1, description="最大 token 数")
    enable_memory: bool = Field(default=True, description="是否启用记忆")
    enable_tools: bool = Field(default=True, description="是否启用工具")
    enable_rag: bool = Field(default=False, description="是否启用 RAG")
    enable_agent: bool = Field(default=False, description="是否启用 Agent 自动执行")
