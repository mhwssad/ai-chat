"""FastAPI 异常处理。"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.ai.core.tools import ToolError
from src.ai.exception.base_exception import BaseExceptions
from src.ai.exception.llm_exception import LLMException


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(LLMException)
    async def llm_exception_handler(request: Request, exc: LLMException):
        return JSONResponse(
            status_code=502,
            content={"error": "llm_error", "message": str(exc), "context": getattr(exc, "context", {})},
        )

    @app.exception_handler(ToolError)
    async def tool_exception_handler(request: Request, exc: ToolError):
        return JSONResponse(
            status_code=400,
            content={"error": "tool_error", "message": str(exc), "context": exc.context},
        )

    @app.exception_handler(BaseExceptions)
    async def base_exception_handler(request: Request, exc: BaseExceptions):
        return JSONResponse(
            status_code=400,
            content={
                "error": exc.error_code or exc.__class__.__name__,
                "message": exc.message,
                "context": exc.context,
            },
        )
