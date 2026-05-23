"""运行态数据仓库。

提供运行态表的数据访问层。

使用方式::

    from src.ai.storage.database import get_session
    from src.ai.storage.runtime_repository import ModelCallRepository, AuditLogRepository

    with get_session() as session:
        call_repo = ModelCallRepository(session)
        audit_repo = AuditLogRepository(session)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlmodel import select

from src.ai.storage.base_repository import BaseRepository
from src.ai.storage.runtime_models import (
    AuditLog,
    MemoryEntry,
    Message,
    ModelCall,
    PermissionDecision,
    SchemaVersion,
    Session,
    Summary,
    ToolCall,
)


class SchemaVersionRepository(BaseRepository[SchemaVersion]):
    model = SchemaVersion


class SessionRepository(BaseRepository[Session]):
    model = Session


class MessageRepository(BaseRepository[Message]):
    model = Message

    def get_by_session(self, session_id: str) -> list[Message]:
        return self.list(session_id=session_id, order_by="created_at", descending=False)


class SummaryRepository(BaseRepository[Summary]):
    model = Summary


class ModelCallRepository(BaseRepository[ModelCall]):
    """模型调用记录仓库。"""

    model = ModelCall

    def get_by_session(self, session_id: str) -> list[ModelCall]:
        """获取指定会话的所有调用记录。"""
        return self.list(session_id=session_id, order_by="created_at", descending=True)

    def get_by_model(self, model: str, *, limit: int = 50) -> list[ModelCall]:
        """获取指定模型的调用记录。"""
        return self.list(model=model, limit=limit, order_by="created_at", descending=True)

    def get_errors(self, *, limit: int = 50) -> list[ModelCall]:
        """获取所有错误记录。"""
        return self.list(status="error", limit=limit, order_by="created_at", descending=True)

    def get_aggregated_stats(self, *, since: datetime | None = None) -> dict[str, Any]:
        """聚合统计：总调用数、成功数、失败数、总 token、总费用、平均耗时。"""
        base = select(
            func.count(ModelCall.id),
            func.sum(ModelCall.input_tokens),
            func.sum(ModelCall.output_tokens),
            func.sum(ModelCall.total_tokens),
            func.sum(ModelCall.total_cost),
            func.avg(ModelCall.duration_ms),
        )
        if since:
            base = base.where(ModelCall.created_at >= since)
        row = self.session.exec(base).one()

        total = row[0] or 0
        err_base = select(func.count(ModelCall.id)).where(
            ModelCall.status.in_(["error", "failed"])
        )
        if since:
            err_base = err_base.where(ModelCall.created_at >= since)
        errors = self.session.exec(err_base).one() or 0

        return {
            "total_calls": total,
            "success_calls": total - errors,
            "error_calls": errors,
            "total_input_tokens": int(row[1] or 0),
            "total_output_tokens": int(row[2] or 0),
            "total_tokens": int(row[3] or 0),
            "total_cost": float(row[4] or 0),
            "avg_duration_ms": float(row[5]) if row[5] else None,
            "error_rate": round(errors / total, 4) if total else 0.0,
        }

    def get_stats_by_model(self, *, since: datetime | None = None) -> list[dict[str, Any]]:
        """按 model + provider 分组聚合。"""
        stmt = select(
            ModelCall.model,
            ModelCall.provider,
            func.count(ModelCall.id),
            func.sum(ModelCall.total_tokens),
            func.sum(ModelCall.total_cost),
        ).group_by(ModelCall.model, ModelCall.provider)
        if since:
            stmt = stmt.where(ModelCall.created_at >= since)
        rows = self.session.exec(stmt).all()
        return [
            {
                "model": r[0],
                "provider": r[1],
                "calls": r[2],
                "total_tokens": int(r[3] or 0),
                "total_cost": float(r[4] or 0),
            }
            for r in rows
        ]


class PermissionDecisionRepository(BaseRepository[PermissionDecision]):
    """权限决策仓库。"""

    model = PermissionDecision


class ToolCallRepository(BaseRepository[ToolCall]):
    """工具调用记录仓库。"""

    model = ToolCall


class MemoryEntryRepository(BaseRepository[MemoryEntry]):
    """记忆条目仓库。"""

    model = MemoryEntry

    def get_active(self, *, scope: str | None = None, limit: int = 100) -> list[MemoryEntry]:
        filters = {"status": "active"}
        if scope:
            filters["scope"] = scope
        return self.list(limit=limit, order_by="updated_at", descending=True, **filters)


class AuditLogRepository(BaseRepository[AuditLog]):
    """审计日志仓库。"""

    model = AuditLog

    def get_by_event_type(self, event_type: str, *, limit: int = 50) -> list[AuditLog]:
        """按事件类型查询。"""
        return self.list(event_type=event_type, limit=limit, order_by="created_at", descending=True)

    def get_by_session(self, session_id: str) -> list[AuditLog]:
        """获取指定会话的所有审计记录。"""
        return self.list(session_id=session_id, order_by="created_at", descending=True)
