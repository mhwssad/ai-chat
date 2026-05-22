"""Runtime SQLite initialization helpers."""

from __future__ import annotations

from pathlib import Path

from sqlmodel import SQLModel, create_engine

from src.ai_chat.config.base_config import project_root


class RuntimeDatabase:
    """Owns the MVP runtime database engine and schema initialization."""

    def __init__(self, db_path: str = "") -> None:
        self.db_path = Path(db_path) if db_path else project_root / "data" / "runtime.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )

    def create_all(self) -> None:
        """Create all imported SQLModel tables in the runtime database."""
        SQLModel.metadata.create_all(self.engine)


runtime_database = RuntimeDatabase()
