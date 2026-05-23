"""默认模型 provider 注册。"""

from __future__ import annotations

from .providers import (
    HttpxOpenAICompatibleChatProvider,
    HttpxOpenAICompatibleEmbeddingProvider,
    LangChainAnthropicChatProvider,
    LangChainGoogleChatProvider,
    LangChainOllamaChatProvider,
    LangChainOpenAIChatProvider,
)
from .registry import ModelProviderRegistry, provider_registry


def install_default_providers(registry: ModelProviderRegistry = provider_registry) -> None:
    """注册内置 provider。可重复调用。"""
    for provider in (
        LangChainOpenAIChatProvider(),
        LangChainAnthropicChatProvider(),
        LangChainGoogleChatProvider(),
        LangChainOllamaChatProvider(),
        HttpxOpenAICompatibleChatProvider(),
        HttpxOpenAICompatibleEmbeddingProvider(),
    ):
        registry.register(provider)
