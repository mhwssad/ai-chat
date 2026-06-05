"""数据库连接与会话管理模块。

提供统一的数据库引擎和会话管理，支持 SQLite 和其他数据库后端。
所有数据库操作通过此模块获取会话。

使用方式::

    from src.ai.storage.database import get_session, get_engine

    with get_session() as session:
        # 执行数据库操作
        session.add(model)
        session.commit()
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session
from src.ai.config.base_config import get_bootstrap_settings


Base = SQLModel

# 模块级缓存（延迟初始化单例，兼顾容器外直接调用）
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _get_database_url() -> str:
    """获取数据库连接 URL。

    通过 BootstrapSettings 读取启动期数据库配置。

    Returns:
        数据库连接 URL 字符串
    """
    return get_bootstrap_settings().resolved_database_url()


def get_engine() -> Engine:
    """获取数据库引擎实例（单例模式）。

    首次调用时创建引擎，后续调用返回同一实例。

    Returns:
        SQLAlchemy Engine 实例
    """
    global _engine
    if _engine is None:
        database_url = _get_database_url()
        connect_args: dict = {}
        # SQLite 特定配置
        if database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_engine(
            database_url,
            echo=get_bootstrap_settings().sqlalchemy_echo,
            connect_args=connect_args,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """获取会话工厂实例（单例模式）。

    首次调用时创建工厂，后续调用返回同一实例。

    Returns:
        SQLAlchemy sessionmaker 实例
    """
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(
            bind=engine, class_=Session, expire_on_commit=False
        )
    return _session_factory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """获取数据库会话的上下文管理器。

    用法::

        with get_session() as session:
            session.add(some_model)
            session.commit()

    Yields:
        SQLAlchemy Session 实例
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database() -> None:
    """初始化数据库：创建所有表。

    导入所有模型以确保它们被注册到 Base.metadata。
    应在应用启动时调用一次。
    """
    # 导入所有模型以触发 SQLModel 的表注册
    from src.ai.storage import config_models  # noqa: F401
    from src.ai.storage import prompt_models  # noqa: F401
    from src.ai.storage import runtime_models  # noqa: F401
    from src.ai.storage import scheduler_models  # noqa: F401

    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def close_database() -> None:
    """关闭数据库连接池。

    释放引擎资源并重置单例缓存，应在应用关闭时调用。
    """
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
        _engine = None
    _session_factory = None
