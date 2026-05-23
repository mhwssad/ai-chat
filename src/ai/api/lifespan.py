"""FastAPI 生命周期管理。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.ai.storage.database import close_database, init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield
    close_database()

