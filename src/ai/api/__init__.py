"""FastAPI 应用工厂。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.ai.api.error_handlers import register_error_handlers
from src.ai.api.routes.agent import router as agent_router
from src.ai.api.routes.chat import router as chat_router
from src.ai.api.routes.image import router as image_router
from src.ai.api.routes.memory import router as memory_router
from src.ai.api.routes.models import router as models_router
from src.ai.api.routes.prompts import router as prompts_router
from src.ai.api.routes.rag import router as rag_router
from src.ai.api.routes.scheduler import router as scheduler_router
from src.ai.api.routes.sessions import router as sessions_router
from src.ai.api.routes.skills import router as skills_router
from src.ai.api.routes.tools import router as tools_router
from src.ai.api.routes.tts import router as tts_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。

    启动时初始化服务，关闭时清理资源。
    """
    from src.ai.core.container_wiring import initialize_container, shutdown_container

    # 初始化：建表、种子模板、技能发现、工具注册、调度器启动
    initialize_container()

    yield

    # 关闭时停止调度器
    shutdown_container()


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    app = FastAPI(
        title="AI Chat",
        description="本地 AI 工作台",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 注册异常处理器
    register_error_handlers(app)

    # CORS 中间件（允许前端开发服务器访问）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(agent_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(image_router, prefix="/api/v1")
    app.include_router(memory_router, prefix="/api/v1")
    app.include_router(models_router, prefix="/api/v1")
    app.include_router(prompts_router, prefix="/api/v1")
    app.include_router(rag_router, prefix="/api/v1")
    app.include_router(scheduler_router, prefix="/api/v1")
    app.include_router(sessions_router, prefix="/api/v1")
    app.include_router(skills_router, prefix="/api/v1")
    app.include_router(tools_router, prefix="/api/v1")
    app.include_router(tts_router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        """健康检查。"""
        return {"status": "ok"}

    return app


app = create_app()
