"""通用模型请求客户端。"""

from __future__ import annotations

import time

from src.ai.exception.llm_exception import LLMException
from src.ai.storage.database import get_session as default_session_factory

from .pricing import PricingCalculator
from .registry import ModelProviderRegistry, provider_registry
from .resolver import ModelResolver
from .telemetry import ModelTelemetryRecorder
from .types import ChatRequest, EmbeddingRequest, ModelRequest, ModelResponse, ModelStreamChunk, ModelUsage


class ModelClient:
    """只编排模型请求和响应，不包含 provider 细节。"""

    def __init__(
        self,
        *,
        registry: ModelProviderRegistry = provider_registry,
        resolver: ModelResolver | None = None,
        pricing: PricingCalculator | None = None,
        telemetry: ModelTelemetryRecorder | None = None,
    ) -> None:
        self._registry = registry
        self._resolver = resolver or ModelResolver()
        self._pricing = pricing or PricingCalculator()
        self._telemetry = telemetry or ModelTelemetryRecorder()

    def chat(self, request: ChatRequest) -> ModelResponse:
        """发起一次非流式聊天请求。"""
        return self._request(request)

    def chat_stream(self, request: ChatRequest):
        """发起一次流式聊天请求。"""
        return self._stream(request)

    def embedding(self, request: EmbeddingRequest) -> ModelResponse:
        """发起一次 embedding 请求。"""
        return self._request(request)

    def _request(self, request: ModelRequest) -> ModelResponse:
        started = time.perf_counter()
        with default_session_factory() as session:
            provider, model = self._resolver.resolve(session, request)
            try:
                model_provider = self._resolve_provider(request.capability, model.request_type)
                response = model_provider.request(provider=provider, model=model, request=request)
                response = self._with_cost(response=response, model=model)
                duration_ms = int((time.perf_counter() - started) * 1000)
                self._telemetry.record_success(
                    session=session,
                    request=request,
                    response=response,
                    provider=provider,
                    model=model,
                    duration_ms=duration_ms,
                )
                session.commit()
                return response
            except Exception as exc:
                duration_ms = int((time.perf_counter() - started) * 1000)
                self._telemetry.record_failure(
                    session=session,
                    request=request,
                    provider=provider,
                    model=model,
                    duration_ms=duration_ms,
                    exc=exc,
                )
                session.commit()
                if isinstance(exc, LLMException):
                    raise
                raise LLMException(
                    "模型请求失败",
                    context={
                        "provider": provider.provider_key,
                        "model": model.model_key,
                        "capability": request.capability,
                        "error": str(exc),
                    },
                ) from exc

    def _resolve_provider(self, capability: str, request_type: str):
        try:
            return self._registry.get(capability, request_type)
        except LLMException:
            if capability == "chat" and request_type == "openai_compatible":
                return self._registry.get("chat", "httpx_openai_compatible")
            raise

    def _stream(self, request: ChatRequest):
        started = time.perf_counter()
        with default_session_factory() as session:
            provider, model = self._resolver.resolve(session, request)
            chunks: list[str] = []
            last_chunk: ModelStreamChunk | None = None
            try:
                model_provider = self._resolve_provider(request.capability, model.request_type)
                for chunk in model_provider.stream(
                    provider=provider,
                    model=model,
                    request=request,
                ):
                    last_chunk = chunk
                    if chunk.delta:
                        chunks.append(chunk.delta)
                    yield chunk

                usage = last_chunk.usage if last_chunk else None
                response = ModelResponse(
                    content="".join(chunks),
                    provider=provider.provider_key,
                    model=model.model_key,
                    capability=request.capability,
                    usage=usage or ModelUsage(),
                    request_id=last_chunk.request_id if last_chunk else None,
                    raw={"stream": True},
                )
                response = self._with_cost(response=response, model=model)
                duration_ms = int((time.perf_counter() - started) * 1000)
                self._telemetry.record_success(
                    session=session,
                    request=request,
                    response=response,
                    provider=provider,
                    model=model,
                    duration_ms=duration_ms,
                )
                session.commit()
            except Exception as exc:
                duration_ms = int((time.perf_counter() - started) * 1000)
                self._telemetry.record_failure(
                    session=session,
                    request=request,
                    provider=provider,
                    model=model,
                    duration_ms=duration_ms,
                    exc=exc,
                )
                session.commit()
                if isinstance(exc, LLMException):
                    raise
                raise LLMException(
                    "模型流式请求失败",
                    context={
                        "provider": provider.provider_key,
                        "model": model.model_key,
                        "capability": request.capability,
                        "error": str(exc),
                    },
                ) from exc

    def _with_cost(self, *, response: ModelResponse, model) -> ModelResponse:
        cost = self._pricing.calculate(response.usage, model)
        if cost.total_cost is None:
            return response
        return ModelResponse(
            content=response.content,
            provider=response.provider,
            model=response.model,
            capability=response.capability,
            usage=response.usage,
            cost=cost,
            request_id=response.request_id,
            raw=response.raw,
        )


def create_chat_completion(request: ChatRequest) -> ModelResponse:
    """便捷函数：发起一次非流式聊天请求。"""
    return ModelClient().chat(request)


def create_chat_completion_stream(request: ChatRequest):
    """便捷函数：发起一次流式聊天请求。"""
    return ModelClient().chat_stream(request)


def create_embedding(request: EmbeddingRequest) -> ModelResponse:
    """便捷函数：发起一次 embedding 请求。"""
    return ModelClient().embedding(request)
