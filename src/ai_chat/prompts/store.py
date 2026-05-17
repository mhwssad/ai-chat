from __future__ import annotations

"""Prompts SQLite 持久化存储 — 基于 SQLModel ORM 的 CRUD 操作。

数据库文件: {project_root}/data/prompts.db
表: prompts + schema_meta（版本追踪）
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import func as sa_func, text as sa_text
from sqlalchemy import delete as sa_delete
from sqlmodel import Session as SqlSession, create_engine, select, col

from src.ai_chat.config.base_config import project_root
from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.prompts.models import (
    PromptCreateRequest,
    PromptRecord,
    PromptTable,
    PromptVersionRecord,
    PromptVersionTable,
)

logger = get_logger(__name__)

# 当前 schema 版本号
_SCHEMA_VERSION = 3


def _table_to_record(row: PromptTable) -> PromptRecord:
    """PromptTable ORM 行 → PromptRecord 传输对象。"""
    return PromptRecord(
        id=row.id,
        name=row.name,
        source_type=row.source_type,
        content=row.content,
        file_path=row.file_path,
        input_variables=row.input_variables or [],
        description=row.description,
        tags=row.tags,
        is_builtin=row.is_builtin,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _version_to_record(row: PromptVersionTable) -> PromptVersionRecord:
    """PromptVersionTable ORM 行 → PromptVersionRecord 传输对象。"""
    return PromptVersionRecord(
        id=row.id,
        prompt_name=row.prompt_name,
        content=row.content,
        file_path=row.file_path,
        source_type=row.source_type,
        input_variables=row.input_variables or [],
        description=row.description,
        tags=row.tags,
        created_at=row.created_at,
    )


class PromptStore:
    """提示词 SQLite 持久化存储。

    支持轻量 schema 迁移：通过 schema_meta 表记录版本号，
    启动时对比 _SCHEMA_VERSION 并按序执行迁移函数。
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        path = db_path or str(project_root / "data" / "prompts.db")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{path}", echo=False)
        self._init_db()
        self._ensure_schema()
        logger.info("PromptStore 初始化完成: %s (schema v%d)", path, _SCHEMA_VERSION)

    def _init_db(self) -> None:
        from sqlmodel import SQLModel as _Base
        _Base.metadata.create_all(self._engine)

    # ── Schema 迁移 ──────────────────────────────────

    def _ensure_schema(self) -> None:
        """检查并执行 schema 迁移。"""
        with self._engine.connect() as conn:
            conn.execute(sa_text(
                "CREATE TABLE IF NOT EXISTS schema_meta (version INTEGER NOT NULL)"
            ))
            conn.commit()
            result = conn.execute(sa_text("SELECT version FROM schema_meta")).first()
            current = result[0] if result else 0

        if current < _SCHEMA_VERSION:
            for version, migration_fn in _MIGRATIONS:
                if current < version:
                    logger.info("迁移 schema: v%d -> v%d", current, version)
                    migration_fn(self._engine)
                    current = version
            with self._engine.connect() as conn:
                conn.execute(sa_text("DELETE FROM schema_meta"))
                conn.execute(sa_text(
                    f"INSERT INTO schema_meta (version) VALUES ({_SCHEMA_VERSION})"
                ))
                conn.commit()

        # 迁移完成后确保索引和 WAL 模式
        with self._engine.connect() as conn:
            conn.execute(sa_text(
                "CREATE INDEX IF NOT EXISTS ix_prompts_tags ON prompts (tags)"
            ))
            conn.execute(sa_text("PRAGMA journal_mode=WAL"))
            conn.commit()

    # ── CRUD ──────────────────────────────────────────

    def create(
        self,
        request: PromptCreateRequest,
        *,
        is_builtin: bool = False,
        input_variables: list[str] | None = None,
    ) -> PromptRecord:
        """创建提示词记录（单次事务，含变量列表）。"""
        now = datetime.now()
        row = PromptTable(
            name=request.name,
            source_type=request.source_type,
            content=request.content,
            file_path=request.file_path,
            input_variables=input_variables or [],
            description=request.description,
            tags=request.tags,
            is_builtin=is_builtin,
            created_at=now,
            updated_at=now,
        )
        with SqlSession(self._engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            result = _table_to_record(row)
        logger.debug("创建提示词: %s (type=%s)", request.name, request.source_type)
        return result

    def get(self, name: str) -> PromptRecord:
        """按名称查询提示词。"""
        with SqlSession(self._engine) as session:
            row = session.exec(
                select(PromptTable).where(PromptTable.name == name)
            ).first()
            if row is None:
                raise KeyError(f"提示词 '{name}' 不存在")
            return _table_to_record(row)

    def get_by_id(self, id: int) -> PromptRecord:
        """按 ID 查询提示词。"""
        with SqlSession(self._engine) as session:
            row = session.get(PromptTable, id)
            if row is None:
                raise KeyError(f"提示词 ID {id} 不存在")
            return _table_to_record(row)

    def list(self, limit: int = 50, offset: int = 0) -> list[PromptRecord]:
        """列出提示词，按名称排序。"""
        with SqlSession(self._engine) as session:
            rows = session.exec(
                select(PromptTable)
                .order_by(col(PromptTable.name).asc())
                .limit(limit).offset(offset)
            ).all()
            return [_table_to_record(r) for r in rows]

    def update(self, name: str, **fields) -> PromptRecord:
        """更新提示词字段。"""
        with SqlSession(self._engine) as session:
            row = session.exec(
                select(PromptTable).where(PromptTable.name == name)
            ).first()
            if row is None:
                raise KeyError(f"提示词 '{name}' 不存在")
            for key, value in fields.items():
                if hasattr(row, key) and value is not None:
                    setattr(row, key, value)
            row.updated_at = datetime.now()
            session.add(row)
            session.commit()
            session.refresh(row)
            result = _table_to_record(row)
        logger.debug("更新提示词: %s, fields=%s", name, list(fields.keys()))
        return result

    def delete(self, name: str) -> None:
        """删除提示词。"""
        with SqlSession(self._engine) as session:
            row = session.exec(
                select(PromptTable).where(PromptTable.name == name)
            ).first()
            if row:
                session.delete(row)
                session.commit()
        logger.debug("删除提示词: %s", name)

    def count(self) -> int:
        """返回提示词总数。"""
        with SqlSession(self._engine) as session:
            result = session.exec(select(sa_func.count()).select_from(PromptTable)).one()
        return result

    def search(self, keyword: str, limit: int = 50, offset: int = 0) -> list[PromptRecord]:
        """按名称、描述或标签模糊搜索。"""
        with SqlSession(self._engine) as session:
            rows = session.exec(
                select(PromptTable)
                .where(
                    col(PromptTable.name).contains(keyword)
                    | col(PromptTable.description).contains(keyword)
                    | col(PromptTable.tags).contains(keyword)
                )
                .order_by(col(PromptTable.name).asc())
                .limit(limit).offset(offset)
            ).all()
            return [_table_to_record(r) for r in rows]

    def exists(self, name: str) -> bool:
        """检查提示词是否存在。"""
        with SqlSession(self._engine) as session:
            row = session.exec(
                select(PromptTable).where(PromptTable.name == name)
            ).first()
            return row is not None

    # ── 版本历史 ──────────────────────────────────────

    # 每个提示词最多保留的历史版本数
    MAX_VERSIONS_PER_PROMPT = 20

    def create_version(self, record: PromptRecord) -> PromptVersionRecord:
        """将当前记录备份到版本历史表，超出上限时自动清理最旧版本。"""
        row = PromptVersionTable(
            prompt_name=record.name,
            content=record.content,
            file_path=record.file_path,
            source_type=record.source_type,
            input_variables=record.input_variables or [],
            description=record.description,
            tags=record.tags,
        )
        with SqlSession(self._engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            result = _version_to_record(row)
            # 清理超出上限的旧版本
            self._cleanup_versions(session, record.name)
        logger.debug("备份版本: %s (v%d)", record.name, result.id)
        return result

    def _cleanup_versions(self, session, name: str) -> None:
        """删除超出上限的最旧版本记录。"""
        total = session.exec(
            select(sa_func.count())
            .select_from(PromptVersionTable)
            .where(PromptVersionTable.prompt_name == name)
        ).one()
        if total > self.MAX_VERSIONS_PER_PROMPT:
            cutoff = session.exec(
                select(PromptVersionTable.id)
                .where(PromptVersionTable.prompt_name == name)
                .order_by(col(PromptVersionTable.id).asc())
                .offset(self.MAX_VERSIONS_PER_PROMPT - 1).limit(1)
            ).first()
            if cutoff is not None:
                session.exec(
                    sa_delete(PromptVersionTable)
                    .where(PromptVersionTable.prompt_name == name, PromptVersionTable.id < cutoff)
                )
                session.commit()
                excess = total - self.MAX_VERSIONS_PER_PROMPT
                logger.debug("清理 %s 的 %d 个旧版本", name, excess)

    def list_versions(self, name: str, limit: int = 20, offset: int = 0) -> list[PromptVersionRecord]:
        """列出指定提示词的版本历史（最新在前）。"""
        with SqlSession(self._engine) as session:
            rows = session.exec(
                select(PromptVersionTable)
                .where(PromptVersionTable.prompt_name == name)
                .order_by(col(PromptVersionTable.id).desc())
                .limit(limit).offset(offset)
            ).all()
            return [_version_to_record(r) for r in rows]

    def get_version(self, version_id: int) -> PromptVersionRecord:
        """获取指定版本记录。"""
        with SqlSession(self._engine) as session:
            row = session.get(PromptVersionTable, version_id)
            if row is None:
                raise KeyError(f"版本 ID {version_id} 不存在")
            return _version_to_record(row)


# ── 迁移函数注册 ──────────────────────────────────────

def _migrate_v2_add_tags(engine) -> None:
    """v1 -> v2: 添加 tags 字段（幂等：已存在则跳过）。"""
    with engine.connect() as conn:
        result = conn.execute(sa_text("PRAGMA table_info(prompts)")).fetchall()
        columns = {row[1] for row in result}
        if "tags" not in columns:
            conn.execute(sa_text(
                "ALTER TABLE prompts ADD COLUMN tags TEXT DEFAULT ''"
            ))
            conn.commit()


def _migrate_v3_add_version_table(engine) -> None:
    """v2 -> v3: 创建 prompt_versions 版本历史表。"""
    from sqlmodel import SQLModel as _Base
    # 确保模型已注册后再 create_all
    _Base.metadata.create_all(engine)


_MIGRATIONS: list[tuple[int, callable]] = [  # type: ignore[misc]
    (2, _migrate_v2_add_tags),
    (3, _migrate_v3_add_version_table),
]
"""按版本号升序排列的迁移函数列表。"""
