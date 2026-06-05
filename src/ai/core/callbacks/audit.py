"""基于 langchain_core BaseCallbackHandler 的审计回调。

替代 core 模块中直接打开 get_session() 写审计日志的做法。
所有 DB 写入集中在 callback 中，core 业务代码完全不感知数据库。
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import LLMResult

from src.ai.storage import AuditLogRepository, ToolCallRepository
from src.ai.storage.database import get_session
from src.ai.utils.redaction import redact_for_audit

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuditEvent:
    """统一审计事件。"""

    event_type: str
    source_module: str | None = None
    target: str | None = None
    session_id: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    status: str = "success"
    duration_ms: int | None = None
    permission_decision: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] | None = None


def record_audit_event(event: AuditEvent) -> None:
    """写入统一审计日志，所有摘要字段先经过脱敏与截断。"""
    try:
        with get_session() as session:
            AuditLogRepository(session).create(
                session_id=event.session_id,
                event_type=event.event_type,
                source_module=event.source_module,
                target=event.target,
                input_summary=_safe_summary(event.input_summary),
                output_summary=_safe_summary(event.output_summary),
                status=event.status,
                duration_ms=event.duration_ms,
                permission_decision=event.permission_decision,
                error_type=event.error_type,
                error_message=_safe_summary(event.error_message),
                extra=json.dumps(event.metadata or {}, ensure_ascii=False),
            )
    except Exception:
        logger.debug("审计日志写入失败: %s", event.event_type, exc_info=True)


class AuditCallbackHandler(BaseCallbackHandler):
    """审计回调：将模型调用和工具调用记录写入 DB。

    通过 config={"callbacks": [AuditCallbackHandler()]} 注入 Runnable。
    """

    # 不忽略任何事件类型
    ignore_llm: bool = False
    ignore_chat_model: bool = False
    ignore_tool: bool = False

    def __init__(self) -> None:
        super().__init__()
        self._tool_starts: dict[UUID, float] = {}
        self._tool_inputs: dict[UUID, dict[str, Any]] = {}
        self._tool_names: dict[UUID, str] = {}

    # ── 工具调用审计 ──────────────────────────────────────

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """工具调用开始，记录时间和输入。"""
        self._tool_starts[run_id] = time.perf_counter()
        self._tool_inputs[run_id] = inputs or {}
        self._tool_names[run_id] = serialized.get("name", "unknown")

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """工具调用成功，写入 tool_calls + audit_logs。"""
        started = self._tool_starts.pop(run_id, None)
        tool_name = self._tool_names.pop(run_id, "unknown")
        tool_inputs = self._tool_inputs.pop(run_id, {})
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0

        output_str = _json_summary(output)
        input_str = _json_summary(tool_inputs)

        try:
            with get_session() as session:
                ToolCallRepository(session).create(
                    tool_name=tool_name,
                    source_type=_extract_source_type(kwargs),
                    source_id=_extract_source_id(kwargs),
                    input_summary=input_str,
                    output_summary=output_str,
                    duration_ms=duration_ms,
                    status="success",
                )
            record_audit_event(
                AuditEvent(
                    event_type="tool_call",
                    source_module="tools",
                    target=tool_name,
                    input_summary=input_str,
                    output_summary=output_str,
                    status="success",
                    duration_ms=duration_ms,
                    metadata={
                        "source_type": _extract_source_type(kwargs),
                        "source_id": _extract_source_id(kwargs),
                    },
                )
            )
        except Exception:
            logger.debug("工具审计写入失败: %s", tool_name, exc_info=True)

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """工具调用失败，写入 tool_calls + audit_logs。"""
        started = self._tool_starts.pop(run_id, None)
        tool_name = self._tool_names.pop(run_id, "unknown")
        tool_inputs = self._tool_inputs.pop(run_id, {})
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0

        input_str = _json_summary(tool_inputs)

        try:
            with get_session() as session:
                ToolCallRepository(session).create(
                    tool_name=tool_name,
                    source_type=_extract_source_type(kwargs),
                    source_id=_extract_source_id(kwargs),
                    input_summary=input_str,
                    duration_ms=duration_ms,
                    status="failed",
                    error_type=type(error).__name__,
                    error_message=redact_for_audit(str(error)),
                )
            record_audit_event(
                AuditEvent(
                    event_type="tool_call",
                    source_module="tools",
                    target=tool_name,
                    input_summary=input_str,
                    status="failed",
                    duration_ms=duration_ms,
                    error_type=type(error).__name__,
                    error_message=str(error),
                    metadata={
                        "source_type": _extract_source_type(kwargs),
                        "source_id": _extract_source_id(kwargs),
                    },
                )
            )
        except Exception:
            logger.debug("工具审计写入失败: %s", tool_name, exc_info=True)

    # ── 模型调用审计 ──────────────────────────────────────

    def on_chat_model_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """模型调用完成，写入 model_calls + audit_logs。"""
        for generation in response.generations:
            for gen in generation:
                message = gen.message  # type: ignore[union-attr]
                if not isinstance(message, AIMessage):
                    continue

                model_name = getattr(response, "llm_output", {}).get(
                    "model_name", "unknown"
                )

                try:
                    record_audit_event(
                        AuditEvent(
                            event_type="model_call",
                            source_module="models",
                            target=model_name,
                            input_summary=f"消息数={len(message.content) if isinstance(message.content, list) else 1}",
                            output_summary=str(message.content),
                            status="success",
                        )
                    )
                except Exception:
                    logger.debug("模型审计写入失败", exc_info=True)


def _json_summary(value: Any) -> str:
    """将值序列化为审计摘要。"""
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        text = str(value)
    return redact_for_audit(text, max_length=500)


def _safe_summary(value: Any, *, max_length: int = 500) -> str | None:
    """将审计字段安全脱敏；空值保持为空。"""
    if value is None:
        return None
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except TypeError:
            text = str(value)
    return redact_for_audit(text, max_length=max_length)


def _extract_source_type(kwargs: dict[str, Any]) -> str:
    """从回调 kwargs 提取 source_type。"""
    tags = kwargs.get("tags", [])
    for tag in tags:
        if tag in ("builtin", "mcp", "skill"):
            return tag
    return "builtin"


def _extract_source_id(kwargs: dict[str, Any]) -> str | None:
    """从回调 kwargs 提取 source_id。"""
    metadata = kwargs.get("metadata", {})
    return metadata.get("source_id")
