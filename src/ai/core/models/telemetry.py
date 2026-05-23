"""模型请求遥测记录。"""

from __future__ import annotations

import json
from typing import Any

from src.ai.storage import AuditLogRepository, Model, ModelCallRepository, Provider
from src.ai.utils.redaction import redact_for_audit

from .types import ModelRequest, ModelResponse


class ModelTelemetryRecorder:
    """记录模型调用和审计日志。"""

    def record_success(
        self,
        *,
        session: Any,
        request: ModelRequest,
        response: ModelResponse,
        provider: Provider,
        model: Model,
        duration_ms: int,
    ) -> None:
        input_summary = self.input_summary(request)
        output_summary = redact_for_audit(str(response.content))
        ModelCallRepository(session).create(
            session_id=request.session_id,
            message_id=request.message_id,
            provider_id=provider.id,
            model_id=model.id,
            provider=provider.provider_key,
            model=model.model_key,
            request_id=response.request_id,
            input_summary=input_summary,
            output_summary=output_summary,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.total_tokens,
            input_cost=response.cost.input_cost,
            output_cost=response.cost.output_cost,
            total_cost=response.cost.total_cost,
            currency=response.cost.currency,
            duration_ms=duration_ms,
            status="success",
        )
        AuditLogRepository(session).create(
            session_id=request.session_id,
            event_type="model_call",
            source_module="models",
            target=f"{provider.provider_key}/{model.model_key}",
            input_summary=input_summary,
            output_summary=output_summary,
            status="success",
            duration_ms=duration_ms,
        )

    def record_failure(
        self,
        *,
        session: Any,
        request: ModelRequest,
        provider: Provider,
        model: Model,
        duration_ms: int,
        exc: Exception,
    ) -> None:
        input_summary = self.input_summary(request)
        error_type = type(exc).__name__
        error_message = redact_for_audit(str(exc))
        ModelCallRepository(session).create(
            session_id=request.session_id,
            message_id=request.message_id,
            provider_id=provider.id,
            model_id=model.id,
            provider=provider.provider_key,
            model=model.model_key,
            input_summary=input_summary,
            duration_ms=duration_ms,
            status="failed",
            error_type=error_type,
            error_message=error_message,
        )
        AuditLogRepository(session).create(
            session_id=request.session_id,
            event_type="model_call",
            source_module="models",
            target=f"{provider.provider_key}/{model.model_key}",
            input_summary=input_summary,
            status="failed",
            duration_ms=duration_ms,
            error_type=error_type,
            error_message=error_message,
        )

    def input_summary(self, request: ModelRequest) -> str:
        data = {
            "capability": request.capability,
            "provider_key": request.provider_key,
            "model_key": request.model_key,
            "metadata": request.metadata,
        }
        messages = getattr(request, "messages", None)
        if messages is not None:
            data["messages"] = [message.to_api_dict() for message in messages]
        return redact_for_audit(json.dumps(data, ensure_ascii=False), max_length=500)
