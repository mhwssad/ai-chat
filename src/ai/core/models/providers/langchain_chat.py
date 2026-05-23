"""LangChain 聊天模型 provider。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

from src.ai.exception.llm_exception import LLMException
from src.ai.storage import Model, Provider

from ..adapters.langchain import (
    ai_message_text,
    ensure_ai_message,
    request_id_from_ai_message,
    to_langchain_messages,
    usage_calculator,
)
from ..registry import ModelProvider
from ..tools import normalize_tools
from ..types import ChatRequest, ModelRequest, ModelResponse, ModelStreamChunk, ModelUsage


def _api_key(provider: Provider) -> str:
    api_key = provider.get_api_key()
    if not api_key:
        raise LLMException("供应商缺少 API Key", context={"provider": provider.provider_key})
    return api_key


def _ensure_chat_request(request: ModelRequest) -> ChatRequest:
    if not isinstance(request, ChatRequest):
        raise LLMException("Provider 只支持聊天请求", context={"capability": request.capability})
    return request


@lru_cache(maxsize=1)
def _chat_openai_cls():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI


@lru_cache(maxsize=1)
def _chat_anthropic_cls():
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic


@lru_cache(maxsize=1)
def _chat_google_cls():
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI


@lru_cache(maxsize=1)
def _chat_ollama_cls():
    from langchain_ollama import ChatOllama

    return ChatOllama


class BaseLangChainChatProvider(ModelProvider, ABC):
    """LangChain 聊天 provider 公共流程。"""

    capabilities = ("chat",)

    def request(self, *, provider: Provider, model: Model, request: ModelRequest) -> ModelResponse:
        chat_request = _ensure_chat_request(request)
        llm = self._build_llm(provider=provider, model=model, request=chat_request)
        result = ensure_ai_message(llm.invoke(to_langchain_messages(chat_request.messages)))
        return self._response_from_ai_message(
            provider=provider,
            model=model,
            result=result,
        )

    def stream(self, *, provider: Provider, model: Model, request: ModelRequest):
        chat_request = _ensure_chat_request(request)
        llm = self._build_llm(provider=provider, model=model, request=chat_request)
        request_id: str | None = None
        usage = ModelUsage()
        for raw_chunk in llm.stream(to_langchain_messages(chat_request.messages)):
            chunk = ensure_ai_message(raw_chunk)
            text = ai_message_text(chunk)
            request_id = request_id_from_ai_message(chunk) or request_id
            chunk_usage = usage_calculator.from_langchain_ai_message(chunk)
            usage = chunk_usage if chunk_usage.total_tokens is not None else usage
            yield ModelStreamChunk(
                delta=text,
                provider=provider.provider_key,
                model=model.model_key,
                capability="chat",
                usage=chunk_usage,
                request_id=request_id,
                raw={"response_metadata": getattr(chunk, "response_metadata", {})},
            )
        yield ModelStreamChunk(
            provider=provider.provider_key,
            model=model.model_key,
            capability="chat",
            usage=usage,
            request_id=request_id,
            finish_reason="stop",
        )

    def _build_llm(self, *, provider: Provider, model: Model, request: ChatRequest):
        llm = self._create_llm(provider=provider, model=model, request=request)
        if request.tools:
            llm = llm.bind_tools([tool.input_schema for tool in normalize_tools(request.tools)])
        return llm

    def _response_from_ai_message(self, *, provider: Provider, model: Model, result: Any):
        return ModelResponse(
            content=ai_message_text(result),
            provider=provider.provider_key,
            model=model.model_key,
            capability="chat",
            usage=usage_calculator.from_langchain_ai_message(result),
            request_id=request_id_from_ai_message(result),
            raw={"response_metadata": result.response_metadata},
        )

    @abstractmethod
    def _create_llm(self, *, provider: Provider, model: Model, request: ChatRequest):
        """创建具体 LangChain LLM 实例。"""


class LangChainOpenAIChatProvider(BaseLangChainChatProvider):
    request_types = ("openai", "openai_compatible")

    def _create_llm(self, *, provider: Provider, model: Model, request: ChatRequest):
        return _chat_openai_cls()(
            model=model.model_key,
            api_key=_api_key(provider),
            base_url=provider.base_url,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )


class LangChainAnthropicChatProvider(BaseLangChainChatProvider):
    request_types = ("anthropic",)

    def _create_llm(self, *, provider: Provider, model: Model, request: ChatRequest):
        return _chat_anthropic_cls()(
            model=model.model_key,
            api_key=_api_key(provider),
            base_url=provider.base_url,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )


class LangChainGoogleChatProvider(BaseLangChainChatProvider):
    request_types = ("google", "gemini")

    def _create_llm(self, *, provider: Provider, model: Model, request: ChatRequest):
        return _chat_google_cls()(
            model=model.model_key,
            google_api_key=_api_key(provider),
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
        )


class LangChainOllamaChatProvider(BaseLangChainChatProvider):
    request_types = ("ollama",)

    def _create_llm(self, *, provider: Provider, model: Model, request: ChatRequest):
        return _chat_ollama_cls()(
            model=model.model_key,
            base_url=provider.base_url,
            temperature=request.temperature,
        )

