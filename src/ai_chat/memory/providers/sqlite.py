"""SQLite 持久化存储后端 — 基于 SQLModel ORM。

将所有会话数据（会话、消息、摘要）持久化到本地 SQLite 文件。
默认路径: {project_root}/data/memory.db
支持 token 追踪信息的 metadata 字段存取。
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlmodel import Session as SqlSession, create_engine, select, col
from sqlalchemy import delete as sa_delete

from src.ai_chat.config.base_config import project_root
from src.ai_chat.config.logging_setup import get_logger
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

logger = get_logger(__name__)


@register_memory("sqlite", lambda: MemoryConfig())
class SQLiteStore(MemoryProvider):
    """基于 SQLModel + SQLite 的持久化存储。

    使用 SQLModel ORM 操作三张表: sessions, messages, summaries。
    通过 SQLAlchemy Engine 连接 SQLite 文件，支持多会话并发读写。
    """

    def __init__(self, config: Optional[MemoryConfig] = None) -> None:
        self._config = config or MemoryConfig()
        db_path = self._config.persist_path or str(project_root / "data" / "memory.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self._init_db()
        logger.info("SQLiteStore 初始化完成，数据库路径: %s", db_path)

    def _init_db(self) -> None:
        """创建所有表（若不存在）、索引并启用 WAL 模式。"""
        from sqlmodel import SQLModel as _Base
        from sqlalchemy import text
        _Base.metadata.create_all(self._engine)
        # 确保索引存在（对已有数据库执行迁移）
        with self._engine.connect() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_messages_session_id ON messages (session_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sessions_updated_at ON sessions (updated_at)"))
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.commit()
        logger.debug("数据库表初始化完成")

    # ── Session ────────────────────────────────────────

    def create_session(self, session_id: Optional[str] = None) -> Session:
        """创建新会话，session_id 为空时自动生成 UUID。"""
        sid = session_id or str(uuid.uuid4())
        now = datetime.now()
        row = SessionTable(session_id=sid, created_at=now, updated_at=now)
        with SqlSession(self._engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            result = _table_to_session(row)
        logger.debug("创建会话: %s", sid[:8])
        return result

    def get_session(self, session_id: str) -> Session:
        """获取会话，不存在时抛出 SessionNotFoundException。"""
        with SqlSession(self._engine) as session:
            row = session.get(SessionTable, session_id)
            if row is None:
                logger.warning("会话不存在: %s", session_id[:8])
                raise SessionNotFoundException(session_id)
            return _table_to_session(row)

    def list_sessions(self, limit: int = 50, offset: int = 0) -> list[Session]:
        """列出会话，按 updated_at 降序排列。"""
        with SqlSession(self._engine) as session:
            rows = session.exec(
                select(SessionTable)
                .order_by(col(SessionTable.updated_at).desc())
                .limit(limit).offset(offset)
            ).all()
            return [_table_to_session(r) for r in rows]

    def delete_session(self, session_id: str) -> None:
        """删除会话及其所有消息（依赖级联或显式删除）。"""
        with SqlSession(self._engine) as session:
            row = session.get(SessionTable, session_id)
            if row:
                session.delete(row)
                session.commit()
                logger.info("删除会话: %s", session_id[:8])

    def update_session_timestamp(self, session_id: str) -> None:
        """更新会话的 updated_at 为当前时间。"""
        with SqlSession(self._engine) as session:
            row = session.get(SessionTable, session_id)
            if row:
                row.updated_at = datetime.now()
                session.add(row)
                session.commit()

    def update_session_metadata(self, session_id: str, metadata: dict) -> None:
        """合并更新会话 metadata（不覆盖已有字段）。

        用于存储 last_prompt_tokens 等 token 追踪信息。
        """
        with SqlSession(self._engine) as session:
            row = session.get(SessionTable, session_id)
            if row:
                existing = row.metadata_ or {}
                existing.update(metadata)
                row.metadata_ = existing
                session.add(row)
                session.commit()
                logger.debug("更新会话 metadata: %s, keys=%s", session_id[:8], list(metadata.keys()))

    def delete_messages_before(self, session_id: str, keep_count: int) -> int:
        """删除旧消息，只保留最近 keep_count 条，返回删除数量。"""
        total = self.count_messages(session_id)
        if total <= keep_count:
            return 0
        delete_count = total - keep_count
        with SqlSession(self._engine) as session:
            # 找到保留边界 id（第 keep_count 条消息的 id）
            cutoff = session.exec(
                select(MessageTable.id)
                .where(MessageTable.session_id == session_id)
                .order_by(col(MessageTable.id).asc())
                .offset(keep_count - 1).limit(1)
            ).first()
            if cutoff is not None:
                session.exec(
                    sa_delete(MessageTable)
                    .where(MessageTable.session_id == session_id, MessageTable.id < cutoff)
                )
                session.commit()
        logger.info("裁剪消息: session=%s, 删除 %d 条，保留 %d 条", session_id[:8], delete_count, keep_count)
        return delete_count

    def reset_context(self, session_id: str) -> None:
        """清除会话的所有消息和摘要，但保留会话本身。"""
        with SqlSession(self._engine) as session:
            session.exec(sa_delete(MessageTable).where(MessageTable.session_id == session_id))
            session.exec(sa_delete(SummaryTable).where(SummaryTable.session_id == session_id))
            # 清空 metadata 中的 token 追踪
            sess_row = session.get(SessionTable, session_id)
            if sess_row:
                sess_row.metadata_ = {}
                session.add(sess_row)
            session.commit()
        logger.info("重置上下文: session=%s, 消息和摘要已清空", session_id[:8])

    def count_sessions(self) -> int:
        """返回会话总数。"""
        from sqlalchemy import func
        with SqlSession(self._engine) as session:
            result = session.exec(select(func.count()).select_from(SessionTable)).one()
        return result

    def search_sessions(self, keyword: str, limit: int = 50, offset: int = 0) -> list[Session]:
        """按标题关键词模糊搜索会话。"""
        with SqlSession(self._engine) as session:
            rows = session.exec(
                select(SessionTable)
                .where(col(SessionTable.title).contains(keyword))
                .order_by(col(SessionTable.updated_at).desc())
                .limit(limit).offset(offset)
            ).all()
            return [_table_to_session(r) for r in rows]

    def update_session_title(self, session_id: str, title: str) -> None:
        """更新会话标题。"""
        with SqlSession(self._engine) as session:
            row = session.get(SessionTable, session_id)
            if row:
                row.title = title
                session.add(row)
                session.commit()
                logger.info("重命名会话: %s -> '%s'", session_id[:8], title)

    # ── 批量查询 ──────────────────────────────────────────

    def batch_count_messages(self, session_ids: list[str]) -> dict[str, int]:
        """批量统计多个会话的消息数量。"""
        if not session_ids:
            return {}
        from sqlalchemy import func
        with SqlSession(self._engine) as session:
            rows = session.exec(
                select(MessageTable.session_id, func.count())
                .where(MessageTable.session_id.in_(session_ids))
                .group_by(MessageTable.session_id)
            ).all()
        result = {sid: 0 for sid in session_ids}
        result.update(dict(rows))
        return result

    def batch_has_summaries(self, session_ids: list[str]) -> dict[str, bool]:
        """批量检查多个会话是否有摘要。"""
        if not session_ids:
            return {}
        with SqlSession(self._engine) as session:
            rows = session.exec(
                select(SummaryTable.session_id)
                .where(SummaryTable.session_id.in_(session_ids))
            ).all()
        existing = set(rows)
        return {sid: sid in existing for sid in session_ids}

    # ── Message ────────────────────────────────────────

    def add_message(self, record: MessageRecord) -> MessageRecord:
        """持久化单条消息，返回填充了自增 id 的记录。"""
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
        logger.debug("添加消息: session=%s, role=%s, id=%d", record.session_id[:8], record.role, record.id)
        return record

    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[MessageRecord]:
        """加载消息，按 id 升序（时间顺序），支持分页。"""
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
        """返回会话中的消息总数。"""
        from sqlalchemy import func
        with SqlSession(self._engine) as session:
            result = session.exec(
                select(func.count()).where(MessageTable.session_id == session_id)
            ).one()
        return result

    # ── Summary ────────────────────────────────────────

    def save_summary(self, session_id: str, summary: str) -> None:
        """保存或更新会话摘要（upsert 语义）。"""
        now = datetime.now()
        with SqlSession(self._engine) as session:
            existing = session.get(SummaryTable, session_id)
            if existing:
                # 更新已有摘要
                existing.summary = summary
                existing.updated_at = now
                session.add(existing)
            else:
                # 首次创建摘要
                session.add(SummaryTable(session_id=session_id, summary=summary, updated_at=now))
            session.commit()
        logger.debug("保存摘要: session=%s, 长度=%d", session_id[:8], len(summary))

    def load_summary(self, session_id: str) -> Optional[str]:
        """加载会话摘要，不存在则返回 None。"""
        with SqlSession(self._engine) as session:
            row = session.get(SummaryTable, session_id)
            return row.summary if row else None
