"""模型 provider 注册表。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from src.ai.exception.llm_exception import LLMException
from src.ai.storage import Model, Provider

from .types import ModelCapability, ModelRequest, ModelResponse


class ModelProvider(ABC):
    """模型 provider 策略接口。"""

    capabilities: ClassVar[tuple[ModelCapability, ...]] = ()
    request_types: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    def request(
        self,
        *,
        provider: Provider,
        model: Model,
        request: ModelRequest,
    ) -> ModelResponse:
        """发起请求并返回统一响应。"""

    def stream(
        self,
        *,
        provider: Provider,
        model: Model,
        request: ModelRequest,
    ):
        """发起流式请求。Provider 可按需覆盖。"""
        raise LLMException(
            "Provider 不支持流式请求",
            context={
                "provider": provider.provider_key,
                "model": model.model_key,
                "capability": request.capability,
            },
        )


class ModelProviderRegistry:
    """按 capability + request_type 查找 provider。"""

    def __init__(self) -> None:
        self._providers: dict[tuple[str, str], ModelProvider] = {}

    def register(self, provider: ModelProvider) -> None:
        for capability in provider.capabilities:
            for request_type in provider.request_types:
                self._providers[(capability, request_type)] = provider

    def get(self, capability: str, request_type: str) -> ModelProvider:
        provider = self._providers.get((capability, request_type))
        if provider is None:
            raise LLMException(
                "未注册的模型请求类型",
                context={"capability": capability, "request_type": request_type},
            )
        return provider


provider_registry = ModelProviderRegistry()


def register_provider(provider: ModelProvider) -> ModelProvider:
    provider_registry.register(provider)
    return provider
