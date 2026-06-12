"""Agent 执行链路追踪 ORM 模型。"""

from datetime import datetime

from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel

from src.ai.storage.utils import dt_now as _dt_now


class AgentTrace(SQLModel, table=True):
    """Agent 执行追踪主表。"""

    __tablename__ = "agent_traces"

    trace_id: str = Field(primary_key=True, description="追踪唯一 ID")
    session_id: str | None = Field(default=None, description="关联会话 ID")
    status: str = Field(default="running", description="追踪状态")
    total_steps: int = Field(default=0, description="总步骤数")
    total_tokens: int = Field(default=0, description="总 token 消耗")
    total_duration_ms: int = Field(default=0, description="总耗时（毫秒）")
    started_at: datetime = Field(default_factory=_dt_now, description="开始时间")
    finished_at: datetime | None = Field(default=None, description="结束时间")
    error_message: str | None = Field(default=None, description="错误消息")
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )


class AgentTraceStepRecord(SQLModel, table=True):
    """Agent 执行步骤记录表。"""

    __tablename__ = "agent_trace_steps"

    id: int | None = Field(default=None, primary_key=True)
    trace_id: str = Field(description="关联追踪 ID")
    step_index: int = Field(description="步骤序号")
    step_type: str = Field(description="步骤类型")
    title: str = Field(default="", description="步骤标题")
    input_summary: str | None = Field(default=None, description="输入摘要")
    output_summary: str | None = Field(default=None, description="输出摘要")
    duration_ms: int = Field(default=0, description="步骤耗时（毫秒）")
    status: str = Field(default="success", description="步骤状态")
    error: str | None = Field(default=None, description="错误信息")
    created_at: datetime = Field(default_factory=_dt_now, description="创建时间")
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )
