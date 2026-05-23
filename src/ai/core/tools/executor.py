"""统一工具执行入口。"""

from __future__ import annotations

import json
import time
from typing import Any

import anyio

from src.ai.storage import AuditLogRepository, ToolCallRepository
from src.ai.storage.database import get_session
from src.ai.utils.redaction import redact_for_audit

from .errors import ToolDisabledError, ToolExecutionError
from .registry import ToolRegistry, tool_registry
from .types import ToolCallRequest, ToolCallResult, ToolDefinition


class ToolExecutor:
    """执行工具并记录调用日志。"""

    def __init__(self, registry: ToolRegistry = tool_registry) -> None:
        self._registry = registry

    async def execute(self, request: ToolCallRequest) -> ToolCallResult:
        tool = self._registry.get(request.tool_name)
        if not tool.enabled:
            raise ToolDisabledError("工具已禁用", context={"tool": request.tool_name})
        if tool.handler is None:
            raise ToolExecutionError("工具未实现", context={"tool": request.tool_name})

        started = time.perf_counter()
        try:
            if tool.timeout_seconds:
                with anyio.fail_after(tool.timeout_seconds):
                    result = await tool.handler(request)
            else:
                result = await tool.handler(request)
            duration_ms = int((time.perf_counter() - started) * 1000)
            self._record_success(tool, request, result, duration_ms)
            return result
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            self._record_failure(tool, request, exc, duration_ms)
            if isinstance(exc, ToolExecutionError):
                raise
            raise ToolExecutionError(
                "工具执行失败",
                context={"tool": request.tool_name, "error": str(exc)},
            ) from exc

    def execute_sync(self, request: ToolCallRequest) -> ToolCallResult:
        return anyio.run(self.execute, request)

    def _record_success(
        self,
        tool: ToolDefinition,
        request: ToolCallRequest,
        result: ToolCallResult,
        duration_ms: int,
    ) -> None:
        output = _json_summary(result.raw or result.structured_content or result.content)
        with get_session() as session:
            ToolCallRepository(session).create(
                session_id=request.session_id,
                message_id=request.message_id,
                tool_name=tool.name,
                source_type=tool.source_type,
                source_id=tool.source_id,
                input_summary=_json_summary(request.arguments),
                output_summary=output,
                duration_ms=duration_ms,
                status="failed" if result.is_error else "success",
            )
            AuditLogRepository(session).create(
                session_id=request.session_id,
                event_type="tool_call",
                source_module="tools",
                target=tool.name,
                input_summary=_json_summary(request.arguments),
                output_summary=output,
                status="failed" if result.is_error else "success",
                duration_ms=duration_ms,
            )

    def _record_failure(
        self,
        tool: ToolDefinition,
        request: ToolCallRequest,
        exc: Exception,
        duration_ms: int,
    ) -> None:
        with get_session() as session:
            ToolCallRepository(session).create(
                session_id=request.session_id,
                message_id=request.message_id,
                tool_name=tool.name,
                source_type=tool.source_type,
                source_id=tool.source_id,
                input_summary=_json_summary(request.arguments),
                duration_ms=duration_ms,
                status="failed",
                error_type=type(exc).__name__,
                error_message=redact_for_audit(str(exc)),
            )
            AuditLogRepository(session).create(
                session_id=request.session_id,
                event_type="tool_call",
                source_module="tools",
                target=tool.name,
                input_summary=_json_summary(request.arguments),
                status="failed",
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
                error_message=redact_for_audit(str(exc)),
            )


def _json_summary(value: Any) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        text = str(value)
    return redact_for_audit(text, max_length=500)


tool_executor = ToolExecutor()

