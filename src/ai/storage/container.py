"""存储子系统 DI 容器。"""

from typing import Any

from dependency_injector import containers, providers


def _create_engine(bootstrap_settings):
    """委托给 database.py 的唯一引擎单例。"""
    from src.ai.storage.database import get_engine

    return get_engine()


def _create_session_factory(engine):
    """委托给 database.py 的唯一会话工厂单例。"""
    from src.ai.storage.database import get_session_factory

    return get_session_factory()


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
