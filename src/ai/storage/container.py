"""存储子系统 DI 容器。"""

from typing import Any

from dependency_injector import containers, providers


def _create_engine(bootstrap_settings):
    """数据库引擎。"""
    from sqlalchemy import create_engine

    database_url = bootstrap_settings.resolved_database_url()
    connect_args: dict = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(
        database_url,
        echo=bootstrap_settings.sqlalchemy_echo,
        connect_args=connect_args,
    )


def _create_session_factory(engine):
    """数据库会话工厂。"""
    from sqlalchemy.orm import sessionmaker
    from sqlmodel import Session

    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def _create_db_prompt_store():
    """数据库提示词存储。"""
    from src.ai.storage.prompt_store import DbPromptStore

    return DbPromptStore()


class StorageContainer(containers.DeclarativeContainer):
    """存储子系统容器。"""

    bootstrap_settings: Any = providers.Dependency()

    engine = providers.Singleton(_create_engine, bootstrap_settings=bootstrap_settings)
    session_factory = providers.Singleton(_create_session_factory, engine=engine)
    db_prompt_store = providers.Singleton(_create_db_prompt_store)
