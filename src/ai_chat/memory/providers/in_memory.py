"""内存存储后端 — 用于测试和无状态场景。"""

import uuid
from datetime import datetime
from typing import Optional

from src.ai_chat.memory.factory import register_memory
from src.ai_chat.memory.models import (
    MemoryConfig,
    MemoryProvider,
    MessageRecord,
    Session,
    SessionNotFoundException,
)


@register_memory("in_memory", lambda: MemoryConfig(backend="in_memory"))
class InMemoryStore(MemoryProvider):
    """进程内存储，退出即丢失。"""

    def __init__(self, config: Optional[MemoryConfig] = None) -> None:
        self._config = config or MemoryConfig(backend="in_memory")
        self._sessions: dict[str, Session] = {}
        self._messages: dict[str, list[MessageRecord]] = {}
        self._summaries: dict[str, str] = {}
        self._auto_id: int = 0

    def create_session(self, session_id: Optional[str] = None) -> Session:
        sid = session_id or str(uuid.uuid4())
        now = datetime.now()
        session = Session(session_id=sid, created_at=now, updated_at=now)
        self._sessions[sid] = session
        self._messages.setdefault(sid, [])
        return session

    def get_session(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            raise SessionNotFoundException(session_id)
        return self._sessions[session_id]

    def list_sessions(self, limit: int = 50, offset: int = 0) -> list[Session]:
        sessions = sorted(
            self._sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True,
        )
        return sessions[offset : offset + limit]

    def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._messages.pop(session_id, None)
        self._summaries.pop(session_id, None)

    def add_message(self, record: MessageRecord) -> MessageRecord:
        self._auto_id += 1
        record.id = self._auto_id
        self._messages.setdefault(record.session_id, []).append(record)
        return record

    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[MessageRecord]:
        msgs = self._messages.get(session_id, [])
        slice_end = None if limit is None else offset + limit
        return msgs[offset:slice_end]

    def count_messages(self, session_id: str) -> int:
        return len(self._messages.get(session_id, []))

    def save_summary(self, session_id: str, summary: str) -> None:
        self._summaries[session_id] = summary

    def load_summary(self, session_id: str) -> Optional[str]:
        return self._summaries.get(session_id)

    def update_session_timestamp(self, session_id: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id].updated_at = datetime.now()
