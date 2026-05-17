"""Google Gemini 聊天模型策略。"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from src.ai_chat.config import settings
from src.ai_chat.llm.factory import register_chat
from src.ai_chat.llm.models import ProviderConfig
from src.ai_chat.llm.providers.chat.base import ChatProvider


@register_chat(
    "gemini",
    lambda: ProviderConfig(
        api_key=settings.get_key(settings.google_api_key),
    ),
)
class GeminiProvider(ChatProvider):
    """Google Gemini 提供商策略。"""

    SUPPORTED_MODELS = [
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()

    def _build_client(self, model_name: str, **kwargs) -> BaseChatModel:
        """构建 Gemini LangChain 客户端。"""
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self._config.api_key,
            temperature=kwargs.get("temperature"),
            max_output_tokens=kwargs.get("max_tokens"),
            timeout=self._config.timeout,
        )
