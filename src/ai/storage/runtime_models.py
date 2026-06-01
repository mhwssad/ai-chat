"""运行态 ORM 模型定义。"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel

from src.ai.storage.utils import dt_now as _dt_now


class ModelCall(SQLModel, table=True):
    """模型调用记录表。"""

    __tablename__ = "model_calls"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str | None = Field(default=None, description="关联会话 ID")
    model: str = Field(description="模型标识")
    request_id: str | None = Field(default=None, description="请求 ID")
    input_summary: str | None = Field(default=None, description="输入摘要（脱敏）")
    output_summary: str | None = Field(default=None, description="输出摘要（脱敏）")
    input_tokens: int | None = Field(default=None, description="输入 token 数")
    output_tokens: int | None = Field(default=None, description="输出 token 数")
    total_tokens: int | None = Field(default=None, description="总 token 数")
    input_cost: float | None = Field(default=None, description="输入费用")
    output_cost: float | None = Field(default=None, description="输出费用")
    total_cost: float | None = Field(default=None, description="总费用")
    currency: str | None = Field(default=None, description="费用币种")
    duration_ms: int | None = Field(default=None, description="调用耗时（毫秒）")
    status: str = Field(default="success", description="调用状态")
    error_type: str | None = Field(default=None, description="错误类型")
    error_message: str | None = Field(default=None, description="错误摘要")
    created_at: datetime = Field(default_factory=_dt_now, description="创建时间")
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )

    def get_metadata(self) -> dict[str, Any]:
        """安全地获取元数据字典。"""
        import json

        if not self.extra:
            return {}
        try:
            return json.loads(self.extra)
        except json.JSONDecodeError:
            return {}

    def set_metadata(self, data: dict[str, Any]) -> None:
        """将字典安全地序列化为 JSON 字符串。"""
        import json

        self.extra = json.dumps(data, ensure_ascii=False)


class ToolCall(SQLModel, table=True):
    """工具调用记录。"""

    __tablename__ = "tool_calls"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str | None = Field(default=None)
    tool_name: str
    source_type: str
    source_id: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    duration_ms: int | None = None
    status: str = Field(default="success")
    error_type: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=_dt_now)
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
    )


class MemoryEntry(SQLModel, table=True):
    """记忆条目索引。"""

    __tablename__ = "memory_entries"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str | None = Field(default=None)
    scope: str = Field(description="记忆作用域")
    memory_type: str = Field(default="project", description="记忆类型")
    source_type: str = Field(description="来源类型")
    source_id: str | None = None
    content_summary: str
    content_ref: str | None = None
    status: str = Field(default="active")
    created_at: datetime = Field(default_factory=_dt_now)
    updated_at: datetime = Field(default_factory=_dt_now)
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
    )


class AuditLog(SQLModel, table=True):
    """通用审计日志表。"""

    __tablename__ = "audit_logs"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str | None = Field(default=None, description="关联会话 ID")
    event_type: str = Field(description="事件类型")
    source_module: str | None = Field(default=None, description="来源模块")
    target: str | None = Field(default=None, description="目标能力或对象")
    input_summary: str | None = Field(default=None, description="输入摘要")
    output_summary: str | None = Field(default=None, description="输出摘要")
    status: str = Field(default="success", description="事件状态")
    duration_ms: int | None = Field(default=None, description="耗时（毫秒）")
    permission_decision: str | None = Field(default=None, description="权限决策摘要")
    error_type: str | None = Field(default=None, description="错误类型")
    error_message: str | None = Field(default=None, description="错误摘要")
    created_at: datetime = Field(default_factory=_dt_now, description="创建时间")
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )
