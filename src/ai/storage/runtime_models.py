"""运行态 ORM 模型定义。"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel

from src.ai.storage.utils import dt_now as _dt_now


class ChatSession(SQLModel, table=True):
    """会话摘要表。"""

    __tablename__ = "chat_sessions"

    session_id: str = Field(primary_key=True, description="会话 ID")
    title: str | None = Field(default=None, description="会话标题")
    current_model: str | None = Field(default=None, description="当前模型")
    status: str = Field(default="active", description="会话状态")
    message_count: int = Field(default=0, description="消息数量")
    created_at: datetime = Field(default_factory=_dt_now, description="创建时间")
    last_active_at: datetime = Field(default_factory=_dt_now, description="最后活动时间")
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )


class ChatMessageStore(SQLModel, table=True):
    """LangChain SQLChatMessageHistory 兼容消息表。"""

    __tablename__ = "chat_message_store"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(description="会话 ID")
    message: str = Field(description="LangChain 消息 JSON")


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


class RagDocument(SQLModel, table=True):
    """RAG 文档索引元信息。"""

    __tablename__ = "rag_documents"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str | None = Field(default=None, description="会话 ID，空表示全局")
    scope: str = Field(default="global", description="索引作用域")
    collection_name: str = Field(description="Chroma collection 名称")
    source_path: str = Field(description="文档来源路径或引用")
    title: str | None = Field(default=None, description="文档标题")
    mime_type: str | None = Field(default=None, description="MIME 类型")
    content_hash: str | None = Field(default=None, description="内容哈希")
    chunk_count: int = Field(default=0, description="分块数量")
    status: str = Field(default="active", description="文档状态")
    indexed_at: datetime = Field(default_factory=_dt_now, description="索引时间")
    updated_at: datetime = Field(default_factory=_dt_now, description="更新时间")
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
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
