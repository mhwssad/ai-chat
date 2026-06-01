"""Anthropic Chat 模型直连构建器 — 使用 langchain_anthropic 直接 SDK。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.ai.core.models.base import ChatModelBuilder

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from src.ai.config.model_settings import ChatModelConfig


class AnthropicChatBuilder(ChatModelBuilder):
    """Anthropic Chat 构建策略。

    使用 langchain_anthropic.ChatAnthropic 直接构建模型，
    绕过 init_chat_model 通用层，减少中间开销。
    """

    backend = ["anthropic"]

    def build(
        self,
        config: ChatModelConfig,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        streaming: bool = False,
    ) -> BaseChatModel:
        from langchain_anthropic import ChatAnthropic

        kwargs: dict = {
            "model": config.model_key,
            "streaming": streaming,
        }
        if config.api_key:
            kwargs["api_key"] = config.api_key
        if config.base_url:
            kwargs["base_url"] = config.base_url
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        return ChatAnthropic(**kwargs)
