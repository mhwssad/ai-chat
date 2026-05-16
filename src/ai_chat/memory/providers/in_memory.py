"""内存存储后端 — 用于测试和无状态场景。

所有数据存储在进程内存的字典中，进程退出后数据丢失。
适合单元测试和不需要持久化的临时场景。
"""

import uuid
from datetime import datetime
from typing import Optional

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.memory.factory import register_memory
from src.ai_chat.memory.models import (
    MemoryConfig,
    MemoryProvider,
    MessageRecord,
    Session,
    SessionNotFoundException,
)

logger = get_logger(__name__)


@register_memory("in_memory", lambda: MemoryConfig(backend="in_memory"))
class InMemoryStore(MemoryProvider):
    """进程内字典存储，退出即丢失。

    数据结构:
    - _sessions: {session_id: Session}
    - _messages: {session_id: [MessageRecord, ...]}
    - _summaries: {session_id: summary_str}
    """

    def __init__(self, config: Optional[MemoryConfig] = None) -> None:
        self._config = config or MemoryConfig(backend="in_memory")
        self._sessions: dict[str, Session] = {}
        self._messages: dict[str, list[MessageRecord]] = {}
        self._summaries: dict[str, str] = {}
        self._auto_id: int = 0
        logger.debug("InMemoryStore 初始化完成")

    def create_session(self, session_id: Optional[str] = None) -> Session:
        """创建新会话，session_id 为空时自动生成 UUID。"""
        sid = session_id or str(uuid.uuid4())
        now = datetime.now()
        session = Session(session_id=sid, created_at=now, updated_at=now)
        self._sessions[sid] = session
        self._messages.setdefault(sid, [])
        logger.debug("创建内存会话: %s", sid[:8])
        return session

    def get_session(self, session_id: str) -> Session:
        """获取会话，不存在时抛出 SessionNotFoundException。"""
        if session_id not in self._sessions:
            raise SessionNotFoundException(session_id)
        return self._sessions[session_id]

    def list_sessions(self, limit: int = 50, offset: int = 0) -> list[Session]:
        """列出会话，按 updated_at 降序排列。"""
        sessions = sorted(
            self._sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True,
        )
        return sessions[offset : offset + limit]

    def delete_session(self, session_id: str) -> None:
        """删除会话及其所有消息和摘要。"""
        self._sessions.pop(session_id, None)
        self._messages.pop(session_id, None)
        self._summaries.pop(session_id, None)
        logger.debug("删除内存会话: %s", session_id[:8])

    def add_message(self, record: MessageRecord) -> MessageRecord:
        """持久化单条消息，分配自增 id。"""
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
        """加载消息，按添加顺序（时间顺序），支持分页。"""
        msgs = self._messages.get(session_id, [])
        slice_end = None if limit is None else offset + limit
        return msgs[offset:slice_end]

    def count_messages(self, session_id: str) -> int:
        """返回会话中的消息总数。"""
        return len(self._messages.get(session_id, []))

    def save_summary(self, session_id: str, summary: str) -> None:
        """保存或覆盖会话摘要。"""
        self._summaries[session_id] = summary

    def load_summary(self, session_id: str) -> Optional[str]:
        """加载会话摘要，不存在则返回 None。"""
        return self._summaries.get(session_id)

    def update_session_timestamp(self, session_id: str) -> None:
        """更新会话的 updated_at 为当前时间。"""
        if session_id in self._sessions:
            self._sessions[session_id].updated_at = datetime.now()

    def update_session_metadata(self, session_id: str, metadata: dict) -> None:
        """合并更新会话 metadata（不覆盖已有字段）。"""
        if session_id in self._sessions:
            existing = self._sessions[session_id].metadata or {}
            existing.update(metadata)
            self._sessions[session_id].metadata = existing

    def delete_messages_before(self, session_id: str, keep_count: int) -> int:
        """删除旧消息，只保留最近 keep_count 条，返回删除数量。"""
        msgs = self._messages.get(session_id, [])
        total = len(msgs)
        if total <= keep_count:
            return 0
        delete_count = total - keep_count
        self._messages[session_id] = msgs[delete_count:]
        logger.debug("裁剪消息: session=%s, 删除 %d 条", session_id[:8], delete_count)
        return delete_count

    def reset_context(self, session_id: str) -> None:
        """清除会话的所有消息和摘要，但保留会话本身。"""
        self._messages[session_id] = []
        self._summaries.pop(session_id, None)
        if session_id in self._sessions:
            self._sessions[session_id].metadata = {}

    def count_sessions(self) -> int:
        """返回会话总数。"""
        return len(self._sessions)

    def search_sessions(self, keyword: str, limit: int = 50, offset: int = 0) -> list[Session]:
        """按标题关键词模糊搜索会话。"""
        matched = [s for s in self._sessions.values() if keyword in s.title]
        matched.sort(key=lambda s: s.updated_at, reverse=True)
        return matched[offset : offset + limit]

    def update_session_title(self, session_id: str, title: str) -> None:
        """更新会话标题。"""
        if session_id in self._sessions:
            self._sessions[session_id].title = title
