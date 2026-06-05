"""运行态数据仓库。"""

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlmodel import select

from src.ai.storage.base_repository import BaseRepository
from src.ai.storage.runtime_models import (
    AuditLog,
    ChatMessageStore,
    ChatSession,
    MemoryEntry,
    ModelCall,
    RagDocument,
    ToolCall,
)


class ChatSessionRepository(BaseRepository[ChatSession]):
    """会话摘要仓库。"""

    model = ChatSession

    def get_by_session_id(self, session_id: str) -> ChatSession | None:
        """按会话 ID 获取摘要。"""
        return self.get_by_id(session_id)

    def touch(
        self,
        session_id: str,
        *,
        title: str | None = None,
        current_model: str | None = None,
        message_count: int | None = None,
    ) -> ChatSession:
        """创建或更新会话活动摘要。"""
        obj = self.get_by_session_id(session_id)
        updates: dict[str, Any] = {}
        if title is not None:
            updates["title"] = title
        if current_model is not None:
            updates["current_model"] = current_model
        if message_count is not None:
            updates["message_count"] = message_count
        updates["last_active_at"] = datetime.now()
        if obj is None:
            return self.create(
                session_id=session_id,
                title=title,
                current_model=current_model,
                message_count=message_count or 0,
                last_active_at=updates["last_active_at"],
            )
        return self.update(obj, **updates)

    def list_active(self, *, limit: int = 100) -> list[ChatSession]:
        """列出活跃会话。"""
        return self.list(
            status="active",
            limit=limit,
            order_by="last_active_at",
            descending=True,
        )


class ChatMessageStoreRepository(BaseRepository[ChatMessageStore]):
    """LangChain 消息表仓库。"""

    model = ChatMessageStore

    def get_by_session(self, session_id: str) -> list[ChatMessageStore]:
        """获取指定会话的原始消息记录。"""
        return self.list(session_id=session_id, order_by="id", descending=False)

    def count_by_session(self, session_id: str) -> int:
        """统计指定会话消息数量。"""
        return self.count(session_id=session_id)


class ModelCallRepository(BaseRepository[ModelCall]):
    """模型调用记录仓库。"""

    model = ModelCall

    def get_by_session(self, session_id: str) -> list[ModelCall]:
        """获取指定会话的所有调用记录。"""
        return self.list(session_id=session_id, order_by="created_at", descending=True)

    def get_by_model(self, model: str, *, limit: int = 50) -> list[ModelCall]:
        """获取指定模型的调用记录。"""
        return self.list(
            model=model, limit=limit, order_by="created_at", descending=True
        )

    def get_errors(self, *, limit: int = 50) -> list[ModelCall]:
        """获取所有错误记录。"""
        return self.list(
            status="failed", limit=limit, order_by="created_at", descending=True
        )

    def get_aggregated_stats(self, *, since: datetime | None = None) -> dict[str, Any]:
        """聚合统计：总调用数、成功数、失败数、总 token、总费用、平均耗时。"""
        base = select(  # type: ignore[call-overload]
            func.count(ModelCall.id),  # type: ignore[arg-type]
            func.sum(ModelCall.input_tokens),  # type: ignore[arg-type]
            func.sum(ModelCall.output_tokens),  # type: ignore[arg-type]
            func.sum(ModelCall.total_tokens),  # type: ignore[arg-type]
            func.sum(ModelCall.total_cost),  # type: ignore[arg-type]
            func.avg(ModelCall.duration_ms),  # type: ignore[arg-type]
        )
        if since:
            base = base.where(ModelCall.created_at >= since)
        row = self.session.exec(base).one()

        total = row[0] or 0
        err_base = select(func.count(ModelCall.id)).where(  # type: ignore[arg-type]
            ModelCall.status.in_(["error", "failed"])  # type: ignore[attr-defined]
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

    def get_stats_by_model(
        self, *, since: datetime | None = None
    ) -> list[dict[str, Any]]:
        """按 model 分组聚合。"""
        stmt = select(
            ModelCall.model,  # type: ignore[arg-type]
            func.count(ModelCall.id),  # type: ignore[arg-type]
            func.sum(ModelCall.total_tokens),  # type: ignore[arg-type]
            func.sum(ModelCall.total_cost),  # type: ignore[arg-type]
        ).group_by(ModelCall.model)
        if since:
            stmt = stmt.where(ModelCall.created_at >= since)
        rows = self.session.exec(stmt).all()
        return [
            {
                "model": r[0],
                "calls": r[1],
                "total_tokens": int(r[2] or 0),
                "total_cost": float(r[3] or 0),
            }
            for r in rows
        ]


class ToolCallRepository(BaseRepository[ToolCall]):
    """工具调用记录仓库。"""

    model = ToolCall


class MemoryEntryRepository(BaseRepository[MemoryEntry]):
    """记忆条目仓库。"""

    model = MemoryEntry

    def get_by_source_id(self, source_id: str) -> MemoryEntry | None:
        """按来源 ID 获取记忆控制面记录。"""
        return self.get_by_field("source_id", source_id)

    def get_active(
        self, *, scope: str | None = None, limit: int = 100
    ) -> list[MemoryEntry]:
        filters = {"status": "active"}
        if scope:
            filters["scope"] = scope
        return self.list(limit=limit, order_by="updated_at", descending=True, **filters)  # type: ignore[arg-type]

    def get_by_type(self, memory_type: str, *, limit: int = 50) -> list[MemoryEntry]:
        """按记忆类型查询活跃条目。"""
        return self.list(
            status="active",
            memory_type=memory_type,
            limit=limit,
            order_by="updated_at",
            descending=True,
        )

    def search_summary(self, keyword: str, *, limit: int = 20) -> list[MemoryEntry]:
        """按关键词搜索 content_summary。"""
        all_entries = self.get_active(limit=500)
        keyword_lower = keyword.lower()
        return [
            e
            for e in all_entries
            if e.content_summary and keyword_lower in e.content_summary.lower()
        ][:limit]


class RagDocumentRepository(BaseRepository[RagDocument]):
    """RAG 文档元信息仓库。"""

    model = RagDocument

    def get_by_source(
        self, source_path: str, *, session_id: str | None = None
    ) -> RagDocument | None:
        """按来源和作用域获取文档记录。"""
        stmt = select(RagDocument).where(RagDocument.source_path == source_path)
        if session_id is None:
            stmt = stmt.where(RagDocument.session_id.is_(None))  # type: ignore[attr-defined]
        else:
            stmt = stmt.where(RagDocument.session_id == session_id)
        return self.session.exec(stmt).first()

    def list_by_scope(self, *, session_id: str | None = None) -> list[RagDocument]:
        """按全局或会话作用域列出文档。"""
        filters: dict[str, Any] = {"status": "active", "session_id": session_id}
        return self.list(order_by="updated_at", descending=True, **filters)


class AuditLogRepository(BaseRepository[AuditLog]):
    """审计日志仓库。"""

    model = AuditLog

    def get_by_event_type(self, event_type: str, *, limit: int = 50) -> list[AuditLog]:
        """按事件类型查询。"""
        return self.list(
            event_type=event_type, limit=limit, order_by="created_at", descending=True
        )

    def get_by_session(self, session_id: str) -> list[AuditLog]:
        """获取指定会话的所有审计记录。"""
        return self.list(session_id=session_id, order_by="created_at", descending=True)
