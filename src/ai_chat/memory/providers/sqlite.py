"""SQLite 持久化存储后端 — 基于 SQLModel ORM。"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlmodel import Session as SqlSession, create_engine, select, col

from src.ai_chat.config.base_config import project_root
from src.ai_chat.memory.factory import register_memory
from src.ai_chat.memory.models import (
    MemoryConfig,
    MemoryProvider,
    MessageRecord,
    Session,
    SessionNotFoundException,
    SessionTable,
    MessageTable,
    SummaryTable,
    _table_to_session,
    _table_to_message_record,
)


@register_memory("sqlite", lambda: MemoryConfig())
class SQLiteStore(MemoryProvider):
    """基于 SQLModel + SQLite 的持久化存储。"""

    def __init__(self, config: Optional[MemoryConfig] = None) -> None:
        self._config = config or MemoryConfig()
        db_path = self._config.persist_path or str(project_root / "data" / "memory.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self._init_db()

    def _init_db(self) -> None:
        from sqlmodel import SQLModel as _Base
        _Base.metadata.create_all(self._engine)

    # ── Session ────────────────────────────────────────

    def create_session(self, session_id: Optional[str] = None) -> Session:
        sid = session_id or str(uuid.uuid4())
        now = datetime.now()
        row = SessionTable(session_id=sid, created_at=now, updated_at=now)
        with SqlSession(self._engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            return _table_to_session(row)

    def get_session(self, session_id: str) -> Session:
        with SqlSession(self._engine) as session:
            row = session.get(SessionTable, session_id)
            if row is None:
                raise SessionNotFoundException(session_id)
            return _table_to_session(row)

    def list_sessions(self, limit: int = 50, offset: int = 0) -> list[Session]:
        with SqlSession(self._engine) as session:
            rows = session.exec(
                select(SessionTable)
                .order_by(col(SessionTable.updated_at).desc())
                .limit(limit).offset(offset)
            ).all()
            return [_table_to_session(r) for r in rows]

    def delete_session(self, session_id: str) -> None:
        with SqlSession(self._engine) as session:
            row = session.get(SessionTable, session_id)
            if row:
                session.delete(row)
                session.commit()

    def update_session_timestamp(self, session_id: str) -> None:
        with SqlSession(self._engine) as session:
            row = session.get(SessionTable, session_id)
            if row:
                row.updated_at = datetime.now()
                session.add(row)
                session.commit()

    # ── Message ────────────────────────────────────────

    def add_message(self, record: MessageRecord) -> MessageRecord:
        row = MessageTable(
            session_id=record.session_id,
            role=record.role,
            content=record.content,
            created_at=record.created_at,
            metadata_=record.metadata,
        )
        with SqlSession(self._engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            record.id = row.id
        return record

    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[MessageRecord]:
        with SqlSession(self._engine) as session:
            stmt = (
                select(MessageTable)
                .where(MessageTable.session_id == session_id)
                .order_by(col(MessageTable.id).asc())
            )
            if limit is not None:
                stmt = stmt.limit(limit).offset(offset)
            rows = session.exec(stmt).all()
            return [_table_to_message_record(r) for r in rows]

    def count_messages(self, session_id: str) -> int:
        from sqlalchemy import func
        with SqlSession(self._engine) as session:
            result = session.exec(
                select(func.count()).where(MessageTable.session_id == session_id)
            ).one()
        return result

    # ── Summary ────────────────────────────────────────

    def save_summary(self, session_id: str, summary: str) -> None:
        now = datetime.now()
        with SqlSession(self._engine) as session:
            existing = session.get(SummaryTable, session_id)
            if existing:
                existing.summary = summary
                existing.updated_at = now
                session.add(existing)
            else:
                session.add(SummaryTable(session_id=session_id, summary=summary, updated_at=now))
            session.commit()

    def load_summary(self, session_id: str) -> Optional[str]:
        with SqlSession(self._engine) as session:
            row = session.get(SummaryTable, session_id)
            return row.summary if row else None
