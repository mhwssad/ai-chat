"""SQLite 持久化存储后端。"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.ai_chat.memory.factory import register_memory
from src.ai_chat.memory.models import (
    MemoryConfig,
    MemoryProvider,
    MessageRecord,
    Session,
    SessionNotFoundException,
)

_CREATE_TABLES_SQL = """\
CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    title       TEXT DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    metadata    TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    metadata    TEXT DEFAULT '{}',
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS summaries (
    session_id  TEXT PRIMARY KEY,
    summary     TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
"""


@register_memory("sqlite", lambda: MemoryConfig())
class SQLiteStore(MemoryProvider):
    """基于 SQLite 的持久化存储。"""

    def __init__(self, config: Optional[MemoryConfig] = None) -> None:
        self._config = config or MemoryConfig()
        if self._config.persist_path:
            self._db_path = self._config.persist_path
        else:
            data_dir = Path(__file__).resolve().parents[4] / "data"
            data_dir.mkdir(exist_ok=True)
            self._db_path = str(data_dir / "memory.db")
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_CREATE_TABLES_SQL)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def create_session(self, session_id: Optional[str] = None) -> Session:
        sid = session_id or str(uuid.uuid4())
        now = datetime.now()
        now_iso = now.isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, title, created_at, updated_at, metadata) "
                "VALUES (?, '', ?, ?, '{}')",
                (sid, now_iso, now_iso),
            )
            conn.commit()
        return Session(session_id=sid, created_at=now, updated_at=now)

    def get_session(self, session_id: str) -> Session:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT session_id, title, created_at, updated_at, metadata "
                "FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise SessionNotFoundException(session_id)
        return self._row_to_session(row)

    def list_sessions(self, limit: int = 50, offset: int = 0) -> list[Session]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT session_id, title, created_at, updated_at, metadata "
                "FROM sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._row_to_session(r) for r in rows]

    def delete_session(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()

    def add_message(self, record: MessageRecord) -> MessageRecord:
        now_iso = record.created_at.isoformat()
        metadata_json = json.dumps(record.metadata, ensure_ascii=False)
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO messages (session_id, role, content, created_at, metadata) "
                "VALUES (?, ?, ?, ?, ?) RETURNING id",
                (record.session_id, record.role, record.content, now_iso, metadata_json),
            )
            row = cursor.fetchone()
            conn.commit()
        if row:
            record.id = row[0]
        return record

    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[MessageRecord]:
        if limit is None:
            sql = (
                "SELECT id, session_id, role, content, created_at, metadata "
                "FROM messages WHERE session_id = ? ORDER BY id ASC"
            )
            params: tuple = (session_id,)
        else:
            sql = (
                "SELECT id, session_id, role, content, created_at, metadata "
                "FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT ? OFFSET ?"
            )
            params = (session_id, limit, offset)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_message(r) for r in rows]

    def count_messages(self, session_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return row[0] if row else 0

    def save_summary(self, session_id: str, summary: str) -> None:
        now_iso = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO summaries (session_id, summary, updated_at) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET summary=excluded.summary, updated_at=excluded.updated_at",
                (session_id, summary, now_iso),
            )
            conn.commit()

    def load_summary(self, session_id: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT summary FROM summaries WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return row[0] if row else None

    @staticmethod
    def _row_to_session(row: tuple) -> Session:
        return Session(
            session_id=row[0],
            title=row[1],
            created_at=datetime.fromisoformat(row[2]),
            updated_at=datetime.fromisoformat(row[3]),
            metadata=json.loads(row[4]),
        )

    @staticmethod
    def _row_to_message(row: tuple) -> MessageRecord:
        return MessageRecord(
            id=row[0],
            session_id=row[1],
            role=row[2],
            content=row[3],
            created_at=datetime.fromisoformat(row[4]),
            metadata=json.loads(row[5]),
        )
