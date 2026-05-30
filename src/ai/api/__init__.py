"""FastAPI 应用工厂。"""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    app = FastAPI(
        title="AI Chat",
        description="本地 AI 工作台",
        version="0.1.0",
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        """健康检查。"""
        return {"status": "ok"}

    return app


app = create_app()
