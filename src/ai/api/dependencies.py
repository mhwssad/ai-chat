"""FastAPI 依赖注入。"""

from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session

from src.ai.storage.database import get_session


def db_session() -> Generator[Session, None, None]:
    with get_session() as session:
        yield session

