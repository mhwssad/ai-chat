"""OpenAI-compatible httpx 兜底 provider。"""

from __future__ import annotations

import json
from typing import Any

import httpx

from src.ai.exception.llm_exception import LLMException
from src.ai.storage import Model, Provider
from src.ai.utils.http import create_client

from ..registry import ModelProvider
from ..tools import normalize_tools
from ..types import ChatRequest, ModelRequest, ModelResponse, ModelStreamChunk, ModelUsage
from ..usage import UsageCalculator


class HttpxOpenAICompatibleChatProvider(ModelProvider):
    capabilities = ("chat",)
    request_types = ("httpx_openai_compatible",)

    def __init__(self, http_client: httpx.Client | None = None, timeout: float = 60) -> None:
        self._http_client = http_client
        self._timeout = timeout
        self._usage = UsageCalculator()

    def request(self, *, provider: Provider, model: Model, request: ModelRequest) -> ModelResponse:
        chat_request = self._ensure_chat_request(provider, request)
        payload = self._build_payload(model=model, request=chat_request, stream=False)

        client = self._http_client or create_client(timeout=self._timeout)
        close_client = self._http_client is None
        try:
            http_response = client.post(
                f"{provider.base_url.rstrip('/')}/chat/completions",
                headers=self._headers(provider),
                json=payload,
            )
            http_response.raise_for_status()
            data = http_response.json()
        finally:
            if close_client:
                client.close()

        choices = data.get("choices") or []
        if not choices:
            raise LLMException("模型响应缺少 choices", context={"provider": provider.provider_key})
        content = (choices[0].get("message") or {}).get("content")
        if content is None:
            raise LLMException("模型响应缺少 message.content", context={"provider": provider.provider_key})

        return ModelResponse(
            content=content,
            provider=provider.provider_key,
            model=model.model_key,
            capability="chat",
            usage=self._usage.from_openai_dict(data),
            request_id=data.get("id") or http_response.headers.get("x-request-id"),
            raw=data,
        )

    def stream(self, *, provider: Provider, model: Model, request: ModelRequest):
        chat_request = self._ensure_chat_request(provider, request)
        payload = self._build_payload(model=model, request=chat_request, stream=True)
        client = self._http_client or create_client(timeout=self._timeout)
        close_client = self._http_client is None
        request_id: str | None = None
        final_usage = ModelUsage()
        try:
            with client.stream(
                "POST",
                f"{provider.base_url.rstrip('/')}/chat/completions",
                headers=self._headers(provider),
                json=payload,
            ) as http_response:
                http_response.raise_for_status()
                request_id = http_response.headers.get("x-request-id")
                for line in http_response.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data:"):
                        line = line.removeprefix("data:").strip()
                    if line == "[DONE]":
                        break
                    data = json.loads(line)
                    request_id = data.get("id") or request_id
                    usage = self._usage.from_openai_dict(data)
                    if usage.total_tokens is not None:
                        final_usage = usage
                    choices = data.get("choices") or []
                    delta = ""
                    finish_reason = None
                    if choices:
                        delta = (choices[0].get("delta") or {}).get("content") or ""
                        finish_reason = choices[0].get("finish_reason")
                    yield ModelStreamChunk(
                        delta=delta,
                        provider=provider.provider_key,
                        model=model.model_key,
                        capability="chat",
                        usage=usage,
                        request_id=request_id,
                        finish_reason=finish_reason,
                        raw=data,
                    )
        finally:
            if close_client:
                client.close()

        yield ModelStreamChunk(
            provider=provider.provider_key,
            model=model.model_key,
            capability="chat",
            usage=final_usage,
            request_id=request_id,
            finish_reason="stop",
        )

    def _ensure_chat_request(self, provider: Provider, request: ModelRequest) -> ChatRequest:
        if not isinstance(request, ChatRequest):
            raise LLMException("Provider 只支持聊天请求", context={"capability": request.capability})
        if not provider.base_url:
            raise LLMException("供应商缺少 base_url", context={"provider": provider.provider_key})
        return request

    def _headers(self, provider: Provider) -> dict[str, str]:
        api_key = provider.get_api_key()
        if not api_key:
            raise LLMException("供应商缺少 API Key", context={"provider": provider.provider_key})
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        *,
        model: Model,
        request: ChatRequest,
        stream: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model.model_key,
            "messages": [message.to_api_dict() for message in request.messages],
            "stream": stream,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.tools:
            payload["tools"] = [tool.input_schema for tool in normalize_tools(request.tools)]
        return payload
