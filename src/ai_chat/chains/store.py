"""Chains SQLite 持久化存储 — 基于 SQLModel ORM 的 CRUD 操作。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import func as sa_func, text as sa_text
from sqlmodel import Session as SqlSession, col, create_engine, select

from src.ai_chat.config.base_config import project_root
from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.chains.models import (
    ChainCreateRequest,
    ChainRecord,
    ChainTable,
)

logger = get_logger(__name__)

_SCHEMA_VERSION = 1


def _table_to_record(row: ChainTable) -> ChainRecord:
    """ChainTable ORM 行 → ChainRecord 传输对象。"""
    return ChainRecord(
        id=row.id,
        name=row.name,
        chain_type=row.chain_type,
        model_name=row.model_name,
        config=json.loads(row.config) if row.config else {},
        prompt_context=json.loads(row.prompt_context) if row.prompt_context else {},
        description=row.description,
        tags=row.tags,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class ChainStore:
    """链配置 SQLite 持久化存储。"""

    def __init__(self, db_path: Optional[str] = None) -> None:
        path = db_path or str(project_root / "data" / "chains.db")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{path}", echo=False)
        self._init_db()
        self._ensure_schema()
        logger.info("ChainStore 初始化完成: %s", path)

    def _init_db(self) -> None:
        from sqlmodel import SQLModel as _Base
        _Base.metadata.create_all(self._engine)

    def _ensure_schema(self) -> None:
        with self._engine.connect() as conn:
            conn.execute(sa_text(
                "CREATE TABLE IF NOT EXISTS schema_meta (version INTEGER NOT NULL)"
            ))
            conn.commit()
            result = conn.execute(sa_text("SELECT version FROM schema_meta")).first()
            current = result[0] if result else 0

        if current < _SCHEMA_VERSION:
            with self._engine.connect() as conn:
                conn.execute(sa_text("DELETE FROM schema_meta"))
                conn.execute(sa_text(
                    f"INSERT INTO schema_meta (version) VALUES ({_SCHEMA_VERSION})"
                ))
                conn.execute(sa_text("PRAGMA journal_mode=WAL"))
                conn.commit()

    # ── CRUD ──────────────────────────────────────────

    def create(self, request: ChainCreateRequest) -> ChainRecord:
        """创建链配置记录。"""
        now = datetime.now()
        row = ChainTable(
            name=request.name,
            chain_type=request.chain_type,
            model_name=request.model_name,
            config=json.dumps(request.config, ensure_ascii=False),
            prompt_context=json.dumps(request.prompt_context, ensure_ascii=False),
            description=request.description,
            tags=request.tags,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        with SqlSession(self._engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            result = _table_to_record(row)
        logger.debug("创建链配置: %s (type=%s)", request.name, request.chain_type)
        return result

    def get(self, name: str) -> ChainRecord:
        """按名称查询链配置。"""
        with SqlSession(self._engine) as session:
            row = session.exec(
                select(ChainTable).where(ChainTable.name == name)
            ).first()
            if row is None:
                raise KeyError(f"链配置 '{name}' 不存在")
            return _table_to_record(row)

    def get_by_id(self, id: int) -> ChainRecord:
        """按 ID 查询链配置。"""
        with SqlSession(self._engine) as session:
            row = session.get(ChainTable, id)
            if row is None:
                raise KeyError(f"链配置 ID {id} 不存在")
            return _table_to_record(row)

    def list(self, limit: int = 50, offset: int = 0) -> list[ChainRecord]:
        """列出链配置，按名称排序。"""
        with SqlSession(self._engine) as session:
            rows = session.exec(
                select(ChainTable)
                .order_by(col(ChainTable.name).asc())
                .limit(limit).offset(offset)
            ).all()
            return [_table_to_record(r) for r in rows]

    def update(self, name: str, **fields) -> ChainRecord:
        """更新链配置字段。"""
        with SqlSession(self._engine) as session:
            row = session.exec(
                select(ChainTable).where(ChainTable.name == name)
            ).first()
            if row is None:
                raise KeyError(f"链配置 '{name}' 不存在")
            for key, value in fields.items():
                if hasattr(row, key) and value is not None:
                    # JSON 字段需要序列化
                    if key in ("config", "prompt_context") and isinstance(value, dict):
                        value = json.dumps(value, ensure_ascii=False)
                    setattr(row, key, value)
            row.updated_at = datetime.now()
            session.add(row)
            session.commit()
            session.refresh(row)
            result = _table_to_record(row)
        logger.debug("更新链配置: %s, fields=%s", name, list(fields.keys()))
        return result

    def delete(self, name: str) -> None:
        """删除链配置。"""
        with SqlSession(self._engine) as session:
            row = session.exec(
                select(ChainTable).where(ChainTable.name == name)
            ).first()
            if row:
                session.delete(row)
                session.commit()
        logger.debug("删除链配置: %s", name)

    def count(self) -> int:
        """返回链配置总数。"""
        with SqlSession(self._engine) as session:
            result = session.exec(select(sa_func.count()).select_from(ChainTable)).one()
        return result

    def search(self, keyword: str, limit: int = 50, offset: int = 0) -> list[ChainRecord]:
        """按名称、描述或标签模糊搜索。"""
        with SqlSession(self._engine) as session:
            rows = session.exec(
                select(ChainTable)
                .where(
                    col(ChainTable.name).contains(keyword)
                    | col(ChainTable.description).contains(keyword)
                    | col(ChainTable.tags).contains(keyword)
                )
                .order_by(col(ChainTable.name).asc())
                .limit(limit).offset(offset)
            ).all()
            return [_table_to_record(r) for r in rows]

    def exists(self, name: str) -> bool:
        """检查链配置是否存在。"""
        with SqlSession(self._engine) as session:
            row = session.exec(
                select(ChainTable).where(ChainTable.name == name)
            ).first()
            return row is not None
