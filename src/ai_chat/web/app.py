"""FastAPI + Jinja2 Web 入口。

启动方式::

    uv run uvicorn src.ai_chat.web.app:create_app --factory --reload
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.ai_chat.web.deps import WEB_DIR
from src.ai_chat.web.routers import chains, chat, mcp, memory, skills, tools, workflows


def create_app() -> FastAPI:
    app = FastAPI(title="AI Chat Web")
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

    app.include_router(chat.router)
    app.include_router(tools.router)
    app.include_router(memory.router)
    app.include_router(mcp.router)
    app.include_router(skills.router)
    app.include_router(chains.router)
    app.include_router(workflows.router)

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.ai_chat.web.app:create_app", factory=True, reload=True)
