"""Google Gemini 聊天模型策略。"""

from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI

from src.ai_chat.config import settings
from ..factory import register_chat
from ..models import ChatProvider, ChatRequest, ChatResponse, ProviderConfig, extract_usage


@register_chat("gemini", lambda: ProviderConfig(
    api_key=settings.get_key(settings.google_api_key),
))
class GeminiProvider(ChatProvider):
    """Google Gemini 提供商策略。

    支持模型：gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash …
    """

    SUPPORTED_MODELS = [
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.SUPPORTED_MODELS

    def get_supported_models(self) -> list[str]:
        return list(self.SUPPORTED_MODELS)

    def get_client(self, model_name: str) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self._config.api_key,
        )

    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self._config.api_key,
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
        )
        result = llm.invoke(request.messages)
        return ChatResponse(
            content=result.content,
            model=model_name,
            usage=extract_usage(result),
        )
