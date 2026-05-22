"""MVP runtime database table models.

The existing memory module owns the canonical `sessions`, `messages`, and
`summaries` tables. This module adds cross-cutting runtime tables for model
calls, tool calls, permission decisions, memory index entries, audit events,
system state, and schema version tracking.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON, Index, UniqueConstraint
from sqlmodel import Field, SQLModel

# Import canonical chat persistence tables so create_all can initialize them
# together with the runtime tables when this module is imported.
from src.ai_chat.memory.models import MessageTable, SessionTable, SummaryTable  # noqa: F401


class SchemaVersionTable(SQLModel, table=True):
    """Tracks local schema versions for lightweight migration boundaries."""

    __tablename__ = "schema_versions"
    __table_args__ = (
        UniqueConstraint("schema_name", name="uq_schema_versions_schema_name"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    schema_name: str = Field(index=True)
    version: int = Field(default=1)
    description: str = Field(default="")
    applied_at: datetime = Field(default_factory=datetime.now)


class ModelCallTable(SQLModel, table=True):
    """Records each model invocation and its outcome."""

    __tablename__ = "model_calls"
    __table_args__ = (
        Index("ix_model_calls_session_id", "session_id"),
        Index("ix_model_calls_provider_model", "provider", "model"),
        Index("ix_model_calls_status", "status"),
        Index("ix_model_calls_created_at", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: Optional[str] = Field(default=None, foreign_key="sessions.session_id")
    message_id: Optional[int] = Field(default=None, foreign_key="messages.id")
    provider: str
    model: str
    request_id: Optional[str] = Field(default=None, index=True)
    input_summary: str = Field(default="")
    output_summary: str = Field(default="")
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    duration_ms: float = Field(default=0.0)
    status: str = Field(default="success")
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    metadata_: dict = Field(default={}, sa_column=Column("metadata", JSON))


class PermissionDecisionTable(SQLModel, table=True):
    """Records allow, deny, or ask decisions for tool-like capabilities."""

    __tablename__ = "permission_decisions"
    __table_args__ = (
        Index("ix_permission_decisions_session_id", "session_id"),
        Index("ix_permission_decisions_capability", "capability_name"),
        Index("ix_permission_decisions_result", "decision"),
        Index("ix_permission_decisions_created_at", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: Optional[str] = Field(default=None, foreign_key="sessions.session_id")
    capability_name: str
    capability_source: str = Field(default="")
    permission_scope: str
    decision: str
    reason: str = Field(default="")
    decided_by: str = Field(default="policy")
    created_at: datetime = Field(default_factory=datetime.now)
    metadata_: dict = Field(default={}, sa_column=Column("metadata", JSON))


class ToolCallTable(SQLModel, table=True):
    """Records calls to built-in tools, MCP tools, and skill-derived tools."""

    __tablename__ = "tool_calls"
    __table_args__ = (
        Index("ix_tool_calls_session_id", "session_id"),
        Index("ix_tool_calls_tool_name", "tool_name"),
        Index("ix_tool_calls_source", "source_type", "source_id"),
        Index("ix_tool_calls_status", "status"),
        Index("ix_tool_calls_created_at", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: Optional[str] = Field(default=None, foreign_key="sessions.session_id")
    message_id: Optional[int] = Field(default=None, foreign_key="messages.id")
    permission_decision_id: Optional[int] = Field(
        default=None,
        foreign_key="permission_decisions.id",
    )
    tool_name: str
    source_type: str
    source_id: str = Field(default="")
    input_summary: str = Field(default="")
    output_summary: str = Field(default="")
    duration_ms: float = Field(default=0.0)
    status: str = Field(default="success")
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    metadata_: dict = Field(default={}, sa_column=Column("metadata", JSON))


class MemoryEntryTable(SQLModel, table=True):
    """Stores auditable memory entries and future retrieval index metadata."""

    __tablename__ = "memory_entries"
    __table_args__ = (
        Index("ix_memory_entries_session_id", "session_id"),
        Index("ix_memory_entries_scope", "scope"),
        Index("ix_memory_entries_status", "status"),
        Index("ix_memory_entries_created_at", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: Optional[str] = Field(default=None, foreign_key="sessions.session_id")
    scope: str = Field(default="session")
    source_type: str = Field(default="message")
    source_id: Optional[str] = None
    content_summary: str = Field(default="")
    content_ref: Optional[str] = None
    status: str = Field(default="active")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata_: dict = Field(default={}, sa_column=Column("metadata", JSON))


class AuditLogTable(SQLModel, table=True):
    """Generic audit trail for key runtime events."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_session_id", "session_id"),
        Index("ix_audit_logs_event_type", "event_type"),
        Index("ix_audit_logs_source_module", "source_module"),
        Index("ix_audit_logs_status", "status"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: Optional[str] = Field(default=None, foreign_key="sessions.session_id")
    event_type: str
    source_module: str
    target: str = Field(default="")
    input_summary: str = Field(default="")
    output_summary: str = Field(default="")
    status: str = Field(default="success")
    duration_ms: float = Field(default=0.0)
    permission_decision: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    metadata_: dict = Field(default={}, sa_column=Column("metadata", JSON))


class SystemStateTable(SQLModel, table=True):
    """Stores small runtime state values that are not source-of-truth config."""

    __tablename__ = "system_states"
    __table_args__ = (
        UniqueConstraint("state_key", name="uq_system_states_state_key"),
        Index("ix_system_states_scope", "scope"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    state_key: str = Field(index=True)
    state_value: str = Field(default="")
    scope: str = Field(default="global")
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata_: dict = Field(default={}, sa_column=Column("metadata", JSON))
