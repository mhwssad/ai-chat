"""统一异常处理 — 将 BaseExceptions 体系映射为 HTTP 响应。"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.ai.exception.base_exception import BaseExceptions
from src.ai.exception.llm_exception import (
    LLMCircuitOpenError,
    LLMException,
    LLMRetryExhaustedError,
    ModelNotSupportedException,
)
from src.ai.exception.mcp_exception import (
    MCPConnectionError,
    MCPError,
    MCPProtocolError,
    MCPToolCallError,
)
from src.ai.exception.media_exception import (
    ImageGenerationException,
    MediaNotFoundError,
    TTSException,
)
from src.ai.exception.memory_exception import MemoryNotFoundError
from src.ai.exception.prompt_exception import (
    PromptError,
    PromptNotFoundError,
    PromptRenderError,
)
from src.ai.exception.rag_exception import RagError
from src.ai.exception.scheduler_exception import SchedulerError, SchedulerNotFoundError
from src.ai.exception.skill_exception import (
    SkillError,
    SkillNotFoundError,
)
from src.ai.exception.tool_exception import (
    ToolDisabledError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionError,
)

logger = logging.getLogger(__name__)

# 异常 → HTTP 状态码映射
_EXCEPTION_STATUS_MAP: dict[type[Exception], int] = {
    # 404 Not Found
    ToolNotFoundError: 404,
    PromptNotFoundError: 404,
    SkillNotFoundError: 404,
    SchedulerNotFoundError: 404,
    MemoryNotFoundError: 404,
    MediaNotFoundError: 404,
    # 403 Forbidden
    ToolPermissionError: 403,
    # 409 Conflict
    ToolDisabledError: 409,
    # 422 Unprocessable Entity
    ToolExecutionError: 422,
    PromptRenderError: 422,
    # 429 Too Many Requests
    LLMCircuitOpenError: 429,
    LLMRetryExhaustedError: 429,
    # 502 Bad Gateway
    MCPConnectionError: 502,
    MCPProtocolError: 502,
    MCPToolCallError: 502,
    ImageGenerationException: 502,
    TTSException: 502,
    # 503 Service Unavailable
    ModelNotSupportedException: 503,
}


def register_error_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。

    Args:
        app: FastAPI 应用实例。
    """

    @app.exception_handler(BaseExceptions)
    async def base_exception_handler(
        request: Request, exc: BaseExceptions
    ) -> JSONResponse:
        """处理所有 BaseExceptions 子类。"""
        status_code = 500

        # 按 MRO 查找最具体的匹配
        for exc_type, code in _EXCEPTION_STATUS_MAP.items():
            if isinstance(exc, exc_type):
                status_code = code
                break

        # 特殊处理：ToolError、PromptError、SkillError、MemoryError、RagError、LLMException、MCPError
        if status_code == 500:
            if isinstance(exc, ToolError):
                status_code = 400
            elif isinstance(exc, PromptError):
                status_code = 400
            elif isinstance(exc, SkillError):
                status_code = 400
            elif isinstance(exc, MemoryNotFoundError):
                status_code = 400
            elif isinstance(exc, RagError):
                status_code = 400
            elif isinstance(exc, SchedulerError):
                status_code = 400
            elif isinstance(exc, LLMException):
                status_code = 500
            elif isinstance(exc, MCPError):
                status_code = 500

        logger.warning(
            "请求异常: %s %s -> %d %s",
            request.method,
            request.url.path,
            status_code,
            exc.message,
            exc_info=status_code >= 500,
        )

        return JSONResponse(
            status_code=status_code,
            content={
                "error": exc.message,
                "error_code": exc.error_code,
                "context": exc.context,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """处理参数验证错误。"""
        logger.warning(
            "参数验证失败: %s %s -> %s",
            request.method,
            request.url.path,
            str(exc),
        )
        return JSONResponse(
            status_code=422,
            content={"error": str(exc)},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """处理未预期的异常。"""
        logger.error(
            "未处理异常: %s %s",
            request.method,
            request.url.path,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "内部服务器错误"},
        )
