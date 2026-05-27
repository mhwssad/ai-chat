"""Chat 模型构建器 + 工厂。

内置 ``InitChatModelBuilder``（基于 langchain ``init_chat_model``），
支持 openai / google_genai / ollama 三种后端。

扩展方式：实现 ``ChatModelBuilder`` 并注册到 ``chat_model_factory``。
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel

from src.ai.config.model_settings import ChatModelConfig
from src.ai.core.models.builders.base import ChatModelBuilder, ModelFactory


# ── 内置构建器 ─────────────────────────────────────────


class InitChatModelBuilder(ChatModelBuilder):
    """通用 Chat 构建策略，使用 langchain ``init_chat_model``。"""

    backend = ["openai", "google_genai", "ollama"]

    def build(
        self,
        config: ChatModelConfig,
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        streaming: bool = False,
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
        return init_chat_model(**kwargs)


# ── Chat 工厂 ──────────────────────────────────────────


class ChatModelFactory(ModelFactory[ChatModelBuilder]):
    """Chat 模型工厂。"""

    def create_builder(self, backend: str) -> ChatModelBuilder:
        return self._resolve(backend, "Chat")
