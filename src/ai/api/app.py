"""FastAPI 应用工厂。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.ai.api.errors import install_exception_handlers
from src.ai.api.lifespan import lifespan
from src.ai.api.routes import api_router, page_router

BASE_DIR = Path(__file__).parent


def create_app() -> FastAPI:
    app = FastAPI(title="AI Chat", version="0.1.0", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    app.include_router(page_router)
    app.include_router(api_router, prefix="/api")
    install_exception_handlers(app)
    return app


app = create_app()

