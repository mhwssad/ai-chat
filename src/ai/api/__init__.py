"""FastAPI 应用入口。

提供 REST API 和前端 SPA 静态文件服务。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.ai.api.routes import api_router
from src.ai.config.logging_setup import get_logger

logger = get_logger(__name__)

# 前端构建产物路径（src/ai/api/__init__.py -> src/front/ai-chat/dist）
_DIST_DIR = Path(__file__).resolve().parent.parent.parent / "front" / "ai-chat" / "dist"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时初始化 DI 容器，关闭时释放资源。"""
    from src.ai.core.container_wiring import initialize_container, shutdown_container

    logger.info("初始化 DI 容器...")
    initialize_container()
    logger.info("AI Chat 服务已启动")

    yield

    logger.info("关闭 DI 容器...")
    shutdown_container()
    logger.info("AI Chat 服务已停止")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    app = FastAPI(
        title="AI Chat",
        description="本地 AI 工作台 API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — 本地开发
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册 API 路由
    app.include_router(api_router, prefix="/api")

    # 挂载前端静态资源（/assets/ 等静态文件）
    if _DIST_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=_DIST_DIR / "assets"), name="static")

        # SPA catch-all：所有非 /api 路径返回 index.html
        @app.get("/{path:path}")
        async def _spa_fallback(path: str, request: Request) -> FileResponse:
            """SPA 前端回退 — 返回 index.html 由 Vue Router 处理。"""
            return FileResponse(_DIST_DIR / "index.html")

    # 全局异常处理
    @app.exception_handler(Exception)
    async def _unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "未处理异常: %s %s -> %s",
            request.method,
            request.url.path,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "内部服务器错误", "error": str(exc)},
        )

    return app


app = create_app()
