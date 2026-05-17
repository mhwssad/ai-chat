"""模型配置持久化 — 数据库驱动的模型注册与热重载。

提供 ModelConfigTable（SQLModel 表）和 ModelConfigStore（CRUD + YAML 种子导入），
让模型列表可通过数据库或配置文件动态管理，无需修改代码或重启服务。

用法::

    from src.ai_chat.llm.model_config import model_config_store

    # 添加外部模型
    model_config_store.add("gpt-4.1", "openai", context_window=128000)

    # 热重载到工厂路由表
    llm_factory.refresh_models()
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlmodel import Field as SQLField
from sqlmodel import Session as SqlSession
from sqlmodel import SQLModel, create_engine, select

from src.ai_chat.config.base_config import project_root
from src.ai_chat.config.logging_setup import get_logger

logger = get_logger(__name__)


class ModelConfigTable(SQLModel, table=True):
    """外部模型配置表。"""

    __tablename__ = "model_configs"

    id: Optional[int] = SQLField(default=None, primary_key=True)
    model_name: str = SQLField(unique=True, index=True)
    provider_name: str
    display_name: Optional[str] = None
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
    is_active: bool = True
    is_builtin: bool = False
    extra_config: Optional[str] = None
    created_at: datetime = SQLField(default_factory=datetime.now)
    updated_at: datetime = SQLField(default_factory=datetime.now)


class ModelConfigStore:
    """模型配置持久化 — SQLite + YAML 种子。"""

    def __init__(self, db_path: str = "") -> None:
        db_path = db_path or str(project_root / "data" / "model_configs.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        SQLModel.metadata.create_all(self._engine)
        logger.info("ModelConfigStore 初始化完成: db=%s", db_path)

    def add(
        self,
        model_name: str,
        provider_name: str,
        *,
        display_name: str | None = None,
        context_window: int | None = None,
        max_output_tokens: int | None = None,
        extra_config: dict | None = None,
    ) -> ModelConfigTable:
        """添加一个外部模型配置。

        Raises:
            ValueError: model_name 已存在时抛出
        """
        with SqlSession(self._engine) as session:
            existing = session.exec(
                select(ModelConfigTable).where(
                    ModelConfigTable.model_name == model_name
                )
            ).first()
            if existing:
                raise ValueError(f"模型 '{model_name}' 已存在")

            row = ModelConfigTable(
                model_name=model_name,
                provider_name=provider_name,
                display_name=display_name,
                context_window=context_window,
                max_output_tokens=max_output_tokens,
                extra_config=json.dumps(extra_config) if extra_config else None,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            logger.info("添加外部模型: %s -> %s", model_name, provider_name)
            return row

    def remove(self, model_name: str) -> bool:
        """移除一个外部模型配置。"""
        with SqlSession(self._engine) as session:
            row = session.exec(
                select(ModelConfigTable).where(
                    ModelConfigTable.model_name == model_name
                )
            ).first()
            if not row:
                return False
            session.delete(row)
            session.commit()
            logger.info("移除外部模型: %s", model_name)
            return True

    def get(self, model_name: str) -> ModelConfigTable | None:
        """按名称获取模型配置。"""
        with SqlSession(self._engine) as session:
            return session.exec(
                select(ModelConfigTable).where(
                    ModelConfigTable.model_name == model_name
                )
            ).first()

    def list_models(
        self,
        provider: str | None = None,
        active_only: bool = True,
    ) -> list[ModelConfigTable]:
        """列出模型配置。"""
        with SqlSession(self._engine) as session:
            stmt = select(ModelConfigTable)
            if active_only:
                stmt = stmt.where(ModelConfigTable.is_active)
            if provider:
                stmt = stmt.where(ModelConfigTable.provider_name == provider)
            return list(session.exec(stmt))

    def update(self, model_name: str, **kwargs) -> ModelConfigTable | None:
        """更新模型配置字段。"""
        with SqlSession(self._engine) as session:
            row = session.exec(
                select(ModelConfigTable).where(
                    ModelConfigTable.model_name == model_name
                )
            ).first()
            if not row:
                return None
            for key, value in kwargs.items():
                if hasattr(row, key):
                    setattr(row, key, value)
            row.updated_at = datetime.now()
            session.add(row)
            session.commit()
            session.refresh(row)
            logger.info("更新外部模型: %s, 字段=%s", model_name, list(kwargs.keys()))
            return row

    def seed_from_yaml(self, yaml_path: str = "") -> int:
        """从 YAML 文件导入模型配置（已存在的跳过）。

        Args:
            yaml_path: YAML 文件路径，默认 data/models.yaml

        Returns:
            新导入的模型数量
        """
        yaml_path = yaml_path or str(project_root / "data" / "models.yaml")
        path = Path(yaml_path)
        if not path.exists():
            logger.debug("YAML 种子文件不存在: %s", yaml_path)
            return 0

        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML 未安装，跳过 YAML 种子导入")
            return 0

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "models" not in data:
            logger.warning("YAML 种子文件格式无效: %s", yaml_path)
            return 0

        count = 0
        for entry in data["models"]:
            name = entry.get("model_name")
            provider = entry.get("provider_name")
            if not name or not provider:
                continue
            if self.get(name):
                continue
            self.add(
                name,
                provider,
                display_name=entry.get("display_name"),
                context_window=entry.get("context_window"),
                max_output_tokens=entry.get("max_output_tokens"),
                extra_config=entry.get("extra_config"),
            )
            count += 1

        if count:
            logger.info("从 YAML 导入 %d 个新模型", count)
        return count


# 模块级单例
model_config_store = ModelConfigStore()
# 启动时自动导入 YAML 种子
model_config_store.seed_from_yaml()
