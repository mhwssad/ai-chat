"""Workflows SQLite 持久化存储 — 基于 SQLModel ORM 的 CRUD 操作。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import func as sa_func, text as sa_text
from sqlmodel import Session as SqlSession, col, create_engine, select

from src.ai_chat.config.base_config import project_root
from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.workflows.models import (
    EdgeConfig,
    NodeConfig,
    WorkflowConfig,
    WorkflowCreateRequest,
    WorkflowRecord,
    WorkflowTable,
)

logger = get_logger(__name__)

_SCHEMA_VERSION = 1


def _table_to_record(row: WorkflowTable) -> WorkflowRecord:
    """WorkflowTable ORM 行 → WorkflowRecord 传输对象。"""
    return WorkflowRecord(
        id=row.id,
        name=row.name,
        description=row.description,
        model_name=row.model_name,
        nodes=[NodeConfig(**n) for n in json.loads(row.nodes)],
        edges=[EdgeConfig(**e) for e in json.loads(row.edges)],
        config=WorkflowConfig(**json.loads(row.config)),
        tags=row.tags,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class WorkflowStore:
    """工作流配置 SQLite 持久化存储。"""

    def __init__(self, db_path: Optional[str] = None) -> None:
        path = db_path or str(project_root / "data" / "workflows.db")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{path}", echo=False)
        self._init_db()
        self._ensure_schema()
        logger.info("WorkflowStore 初始化完成: %s", path)

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

    def create(self, request: WorkflowCreateRequest) -> WorkflowRecord:
        """创建工作流配置记录。"""
        now = datetime.now()
        row = WorkflowTable(
            name=request.name,
            description=request.description,
            model_name=request.model_name,
            nodes=json.dumps([n.model_dump() for n in request.nodes], ensure_ascii=False),
            edges=json.dumps([e.model_dump() for e in request.edges], ensure_ascii=False),
            config=json.dumps(request.config.model_dump(), ensure_ascii=False),
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
        logger.debug("创建工作流: %s", request.name)
        return result

    def get(self, name: str) -> WorkflowRecord:
        """按名称查询工作流配置。"""
        with SqlSession(self._engine) as session:
            row = session.exec(
                select(WorkflowTable).where(WorkflowTable.name == name)
            ).first()
            if row is None:
                raise KeyError(f"工作流 '{name}' 不存在")
            return _table_to_record(row)

    def get_by_id(self, id: int) -> WorkflowRecord:
        """按 ID 查询工作流配置。"""
        with SqlSession(self._engine) as session:
            row = session.get(WorkflowTable, id)
            if row is None:
                raise KeyError(f"工作流 ID {id} 不存在")
            return _table_to_record(row)

    def list(self, limit: int = 50, offset: int = 0) -> list[WorkflowRecord]:
        """列出工作流配置，按名称排序。"""
        with SqlSession(self._engine) as session:
            rows = session.exec(
                select(WorkflowTable)
                .order_by(col(WorkflowTable.name).asc())
                .limit(limit).offset(offset)
            ).all()
            return [_table_to_record(r) for r in rows]

    def update(self, name: str, **fields) -> WorkflowRecord:
        """更新工作流配置字段。"""
        with SqlSession(self._engine) as session:
            row = session.exec(
                select(WorkflowTable).where(WorkflowTable.name == name)
            ).first()
            if row is None:
                raise KeyError(f"工作流 '{name}' 不存在")
            for key, value in fields.items():
                if hasattr(row, key) and value is not None:
                    # JSON 字段需要序列化
                    if key == "nodes" and isinstance(value, list):
                        value = json.dumps([n.model_dump() if hasattr(n, "model_dump") else n for n in value], ensure_ascii=False)
                    elif key == "edges" and isinstance(value, list):
                        value = json.dumps([e.model_dump() if hasattr(e, "model_dump") else e for e in value], ensure_ascii=False)
                    elif key == "config" and isinstance(value, dict):
                        value = json.dumps(value, ensure_ascii=False)
                    setattr(row, key, value)
            row.updated_at = datetime.now()
            session.add(row)
            session.commit()
            session.refresh(row)
            result = _table_to_record(row)
        logger.debug("更新工作流: %s, fields=%s", name, list(fields.keys()))
        return result

    def delete(self, name: str) -> None:
        """删除工作流配置。"""
        with SqlSession(self._engine) as session:
            row = session.exec(
                select(WorkflowTable).where(WorkflowTable.name == name)
            ).first()
            if row:
                session.delete(row)
                session.commit()
        logger.debug("删除工作流: %s", name)

    def count(self) -> int:
        """返回工作流配置总数。"""
        with SqlSession(self._engine) as session:
            result = session.exec(select(sa_func.count()).select_from(WorkflowTable)).one()
        return result

    def search(self, keyword: str, limit: int = 50, offset: int = 0) -> list[WorkflowRecord]:
        """按名称、描述或标签模糊搜索。"""
        with SqlSession(self._engine) as session:
            rows = session.exec(
                select(WorkflowTable)
                .where(
                    col(WorkflowTable.name).contains(keyword)
                    | col(WorkflowTable.description).contains(keyword)
                    | col(WorkflowTable.tags).contains(keyword)
                )
                .order_by(col(WorkflowTable.name).asc())
                .limit(limit).offset(offset)
            ).all()
            return [_table_to_record(r) for r in rows]

    def exists(self, name: str) -> bool:
        """检查工作流配置是否存在。"""
        with SqlSession(self._engine) as session:
            row = session.exec(
                select(WorkflowTable).where(WorkflowTable.name == name)
            ).first()
            return row is not None
