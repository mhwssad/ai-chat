"""OpenAI 聊天模型策略。"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.ai_chat.config import settings
from src.ai_chat.llm.factory import register_chat
from src.ai_chat.llm.models import ProviderConfig
from src.ai_chat.llm.providers.chat.base import ChatProvider


@register_chat(
    "openai",
    lambda: ProviderConfig(
        api_key=settings.get_key(settings.openai_api_key),
        base_url=settings.openai_base_url or None,
    ),
)
class OpenAIProvider(ChatProvider):
    """OpenAI 提供商策略。"""

    SUPPORTED_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "o1",
        "o1-mini",
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()

    def _build_client(self, model_name: str, **kwargs) -> BaseChatModel:
        """构建 OpenAI LangChain 客户端。"""
        return ChatOpenAI(
            model=model_name,
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            temperature=kwargs.get("temperature"),
            max_completion_tokens=kwargs.get("max_tokens"),
            streaming=kwargs.get("streaming", False),
            timeout=self._config.timeout,
        )
