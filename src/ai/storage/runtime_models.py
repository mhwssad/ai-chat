"""运行态 ORM 模型定义。

包含模型调用记录、审计日志等运行态表。
模型信息表（Model）和供应商表（Provider）定义在 model_registry.py 中。
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel


def _dt_now() -> datetime:
    return datetime.now()


class SchemaVersion(SQLModel, table=True):
    """数据库 schema 版本表。"""

    __tablename__ = "schema_versions"

    id: int | None = Field(default=None, primary_key=True)
    schema_name: str = Field(description="schema 名称", unique=True)
    version: int = Field(description="版本号")
    description: str | None = Field(default=None, description="版本说明")
    applied_at: datetime = Field(default_factory=_dt_now, description="应用时间")


class Session(SQLModel, table=True):
    """聊天会话表。"""

    __tablename__ = "sessions"

    session_id: str = Field(primary_key=True, description="会话唯一标识")
    title: str | None = Field(default=None, description="会话标题")
    current_model: str | None = Field(default=None, description="当前模型名称")
    current_model_id: int | None = Field(default=None, description="当前模型 ID")
    message_count: int = Field(default=0, description="消息数量缓存")
    status: str = Field(default="active", description="会话状态")
    last_error: str | None = Field(default=None, description="最近错误摘要")
    created_at: datetime = Field(default_factory=_dt_now, description="创建时间")
    updated_at: datetime = Field(default_factory=_dt_now, description="更新时间")
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )


class Message(SQLModel, table=True):
    """聊天消息表。"""

    __tablename__ = "messages"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(description="所属会话 ID")
    role: str = Field(description="消息角色")
    content: str = Field(description="消息内容")
    model: str | None = Field(default=None, description="模型名称")
    model_id: int | None = Field(default=None, description="模型 ID")
    status: str = Field(default="completed", description="消息状态")
    error_type: str | None = Field(default=None, description="错误类型")
    error_message: str | None = Field(default=None, description="错误摘要")
    created_at: datetime = Field(default_factory=_dt_now, description="创建时间")
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )


class Summary(SQLModel, table=True):
    """会话摘要表。"""

    __tablename__ = "summaries"

    session_id: str = Field(primary_key=True, description="会话 ID")
    summary: str = Field(description="摘要内容")
    updated_at: datetime = Field(default_factory=_dt_now, description="更新时间")


# ================= 模型调用记录 =================


class ModelCall(SQLModel, table=True):
    """模型调用记录表。

    记录每次 LLM API 调用的元信息，用于审计和统计。

    Attributes:
        id: 自增主键
        session_id: 关联会话 ID
        message_id: 关联消息 ID
        provider: 供应商标识
        model: 模型标识
        request_id: 请求 ID
        input_summary: 输入摘要（脱敏）
        output_summary: 输出摘要（脱敏）
        input_tokens: 输入 token 数
        output_tokens: 输出 token 数
        total_tokens: 总 token 数
        duration_ms: 调用耗时（毫秒）
        status: 调用状态（success/error/timeout）
        error_type: 错误类型
        error_message: 错误摘要
        created_at: 创建时间
        metadata: JSON 扩展字段
    """

    __tablename__ = "model_calls"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str | None = Field(default=None, description="关联会话 ID")
    message_id: int | None = Field(default=None, description="关联消息 ID")
    provider_id: int | None = Field(default=None, description="供应商 ID")
    model_id: int | None = Field(default=None, description="模型 ID")
    provider: str = Field(description="供应商标识")
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
    duration_ms: float | None = Field(default=None, description="调用耗时（毫秒）")
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


class PermissionDecision(SQLModel, table=True):
    """权限决策记录。"""

    __tablename__ = "permission_decisions"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str | None = Field(default=None)
    capability_name: str
    capability_source: str | None = None
    permission_scope: str
    decision: str
    reason: str | None = None
    decided_by: str = Field(default="system")
    created_at: datetime = Field(default_factory=_dt_now)
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
    )


class ToolCall(SQLModel, table=True):
    """工具调用记录。"""

    __tablename__ = "tool_calls"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str | None = Field(default=None)
    message_id: int | None = Field(default=None)
    permission_decision_id: int | None = Field(default=None)
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


# ================= 审计日志 =================


class AuditLog(SQLModel, table=True):
    """通用审计日志表。

    记录系统关键事件（模型调用、工具调用、权限决策等），
    用于可观测性和安全审计。

    Attributes:
        id: 自增主键
        session_id: 关联会话 ID
        event_type: 事件类型
        source_module: 来源模块
        target: 目标能力或对象
        input_summary: 输入摘要（脱敏）
        output_summary: 输出摘要（脱敏）
        status: 事件状态
        duration_ms: 耗时（毫秒）
        error_type: 错误类型
        error_message: 错误摘要
        created_at: 创建时间
        metadata: JSON 扩展字段
    """

    __tablename__ = "audit_logs"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str | None = Field(default=None, description="关联会话 ID")
    event_type: str = Field(description="事件类型")
    source_module: str | None = Field(default=None, description="来源模块")
    target: str | None = Field(default=None, description="目标能力或对象")
    input_summary: str | None = Field(default=None, description="输入摘要")
    output_summary: str | None = Field(default=None, description="输出摘要")
    status: str = Field(default="success", description="事件状态")
    duration_ms: float | None = Field(default=None, description="耗时（毫秒）")
    error_type: str | None = Field(default=None, description="错误类型")
    error_message: str | None = Field(default=None, description="错误摘要")
    created_at: datetime = Field(default_factory=_dt_now, description="创建时间")
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )
