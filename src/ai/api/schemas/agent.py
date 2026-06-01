"""Agent Schema。"""

from typing import Any

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    """Agent 执行请求。"""

    session_id: str = Field(description="会话 ID")
    user_message: str = Field(description="用户消息")
    system_prompt: str | None = Field(default=None, description="系统提示")
    max_iterations: int = Field(default=10, description="最大迭代次数")
    tools: list[str] | None = Field(
        default=None, description="可用工具列表（None 表示全部）"
    )


class ToolCallResponse(BaseModel):
    """工具调用响应。"""

    id: str = Field(description="调用 ID")
    name: str = Field(description="工具名称")
    arguments: dict[str, Any] = Field(description="工具参数")
    result: str | None = Field(default=None, description="执行结果")
    error: str | None = Field(default=None, description="错误信息")
    duration_ms: int = Field(default=0, description="执行时长（毫秒）")


class AgentRunResponse(BaseModel):
    """Agent 执行响应。"""

    status: str = Field(description="执行状态")
    content: str = Field(description="响应内容")
    tool_calls: list[ToolCallResponse] = Field(
        default_factory=list, description="工具调用列表"
    )
    iterations: int = Field(description="迭代次数")
    total_tokens: int = Field(description="总 token 数")
    plan: str | None = Field(default=None, description="计划内容")
