"""OpenAI-compatible embedding httpx provider。"""

from __future__ import annotations

from typing import Any

import httpx

from src.ai.exception.llm_exception import LLMException
from src.ai.storage import Model, Provider
from src.ai.utils.http import create_client

from ..registry import ModelProvider
from ..types import EmbeddingRequest, ModelRequest, ModelResponse, ModelUsage


class HttpxOpenAICompatibleEmbeddingProvider(ModelProvider):
    capabilities = ("embedding",)
    request_types = ("openai", "openai_compatible", "httpx_openai_compatible")

    def __init__(self, http_client: httpx.Client | None = None, timeout: float = 60) -> None:
        self._http_client = http_client
        self._timeout = timeout

    def request(self, *, provider: Provider, model: Model, request: ModelRequest) -> ModelResponse:
        if not isinstance(request, EmbeddingRequest):
            raise LLMException("Provider 只支持 embedding 请求", context={"capability": request.capability})
        if not provider.base_url:
            raise LLMException("供应商缺少 base_url", context={"provider": provider.provider_key})
        api_key = provider.get_api_key()
        if not api_key:
            raise LLMException("供应商缺少 API Key", context={"provider": provider.provider_key})

        payload: dict[str, Any] = {"model": model.model_key, "input": request.texts}
        client = self._http_client or create_client(timeout=self._timeout)
        close_client = self._http_client is None
        try:
            http_response = client.post(
                f"{provider.base_url.rstrip('/')}/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            http_response.raise_for_status()
            data = http_response.json()
        finally:
            if close_client:
                client.close()

        vectors = [item["embedding"] for item in sorted(data.get("data") or [], key=lambda item: item.get("index", 0))]
        usage = data.get("usage") or {}
        return ModelResponse(
            content=vectors,
            provider=provider.provider_key,
            model=model.model_key,
            capability="embedding",
            usage=ModelUsage(
                input_tokens=usage.get("prompt_tokens"),
                total_tokens=usage.get("total_tokens"),
            ),
            request_id=data.get("id") or http_response.headers.get("x-request-id"),
            raw=data,
        )

