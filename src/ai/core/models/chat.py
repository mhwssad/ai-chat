"""Chat 模型构建器 + 工厂。

内置 ``InitChatModelBuilder``（基于 langchain ``init_chat_model``），
支持 openai / google_genai / ollama 三种后端。

扩展方式：实现 ``ChatModelBuilder`` 并注册到 ``chat_model_factory``。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.ai.core.models.base import ChatModelBuilder, ModelFactory

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from src.ai.config.model_settings import ChatModelConfig


# ── 内置构建器 ─────────────────────────────────────────

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
            enable_thinking: bool = False,
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
        if enable_thinking:
            kwargs["thinking"] = {"type": "enabled"}
        return ChatAnthropic(**kwargs)


class InitChatModelBuilder(ChatModelBuilder):
    """通用 Chat 构建策略，使用 langchain ``init_chat_model``。"""

    backend = ["openai", "google_genai", "ollama"]

    def build(
            self,
            config: ChatModelConfig,
            *,
            temperature: float | None = None,
            max_tokens: int | None = None,
            streaming: bool = False,
            enable_thinking: bool = False,
    ) -> BaseChatModel:
        from langchain.chat_models import init_chat_model

        kwargs: dict = {
            "model": config.model_key,
            "model_provider": config.backend,
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
        # 注意：OpenAI / google_genai / ollama 标准 API 不支持 enable_thinking，
        # 传递该参数会导致 TypeError。深度思考仅在 Anthropic 后端通过原生 thinking 参数支持。
        return init_chat_model(**kwargs)


# ── Chat 工厂 ──────────────────────────────────────────


class ChatModelFactory(ModelFactory[ChatModelBuilder]):
    """Chat 模型工厂。"""

    def create_builder(self, backend: str) -> ChatModelBuilder:
        return self._resolve(backend, "Chat")
