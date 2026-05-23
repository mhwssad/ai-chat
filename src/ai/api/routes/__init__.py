"""API 路由聚合。"""

from fastapi import APIRouter

from src.ai.api.routes import chat, health, mcp, models, pages, providers, rag, tools, usage

page_router = APIRouter()
page_router.include_router(pages.router)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(providers.router, prefix="/providers", tags=["providers"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(mcp.router, prefix="/mcp", tags=["mcp"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])

__all__ = ["api_router", "page_router"]
