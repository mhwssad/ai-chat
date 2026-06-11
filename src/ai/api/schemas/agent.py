"""Agent 相关请求/响应 Schema。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    """Agent 运行请求。"""

    session_id: str = Field(default="default", description="会话 ID")
    user_message: str = Field(..., min_length=1, description="用户输入")
    system_prompt: str | None = Field(default=None, description="自定义系统提示词")
    max_iterations: int = Field(default=10, ge=1, le=50, description="最大迭代轮数")
    tools: list[str] | None = Field(default=None, description="工具白名单")
    agent_timeout: float = Field(default=300, gt=0, description="超时秒数")


class AgentResumeRequest(BaseModel):
    """Agent 恢复请求。"""

    session_id: str = Field(default="default", description="会话 ID")
    user_message: str = Field(..., min_length=1, description="用户输入")
    max_iterations: int = Field(default=10, ge=1, le=50, description="最大迭代轮数")
    tools: list[str] | None = Field(default=None, description="工具白名单")
    agent_timeout: float = Field(default=300, gt=0, description="超时秒数")


class AgentTeamRequest(BaseModel):
    """Agent 团队请求。"""

    session_id: str = Field(default="default", description="会话 ID")
    user_message: str = Field(..., min_length=1, description="用户输入")
    max_handoffs: int = Field(default=3, ge=1, le=10, description="最大交接次数")


class AgentTraceStepResponse(BaseModel):
    """Agent 执行步骤。"""

    index: int = Field(description="步骤序号")
    step_type: str = Field(description="步骤类型")
    title: str = Field(default="", description="步骤标题")
    summary: str = Field(default="", description="步骤摘要")
    status: str = Field(default="success", description="步骤状态")
    error: str | None = Field(default=None, description="错误信息")


class AgentResultResponse(BaseModel):
    """Agent 运行结果。"""

    status: str = Field(description="运行状态")
    content: str = Field(default="", description="回复内容")
    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list, description="工具调用记录"
    )
    iterations: int = Field(default=0, description="迭代轮数")
    total_tokens: int = Field(default=0, description="总 token 消耗")
    plan: str | None = Field(default=None, description="执行计划")
    trace: list[AgentTraceStepResponse] = Field(
        default_factory=list, description="执行步骤"
    )
    context_sources: list[dict[str, Any]] = Field(
        default_factory=list, description="上下文来源"
    )


class AgentTeamResultResponse(BaseModel):
    """Agent 团队运行结果。"""

    mode: str = Field(description="团队模式")
    final_answer: str = Field(description="最终回答")
    contributions: list[dict[str, Any]] = Field(
        default_factory=list, description="各角色贡献"
    )
    handoffs: list[dict[str, str]] = Field(default_factory=list, description="交接记录")
    winner_role: str | None = Field(default=None, description="获胜角色（辩论模式）")
