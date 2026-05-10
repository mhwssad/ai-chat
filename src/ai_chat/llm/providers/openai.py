"""OpenAI 聊天模型策略。"""

from typing import Iterator, Optional

from langchain_openai import ChatOpenAI

from src.ai_chat.config import settings
from ..factory import register_chat
from ..models import ChatProvider, ChatRequest, ChatResponse, ProviderConfig


@register_chat("openai", lambda: ProviderConfig(
    api_key=settings.get_key(settings.openai_api_key),
    base_url=settings.openai_base_url or None,
))
class OpenAIProvider(ChatProvider):
    """OpenAI 提供商策略。

    支持模型：gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-4, gpt-3.5-turbo, o1, o1-mini …
    """

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

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.SUPPORTED_MODELS

    def get_supported_models(self) -> list[str]:
        return list(self.SUPPORTED_MODELS)

    def get_client(self, model_name: str) -> ChatOpenAI:
        return ChatOpenAI(
            model=model_name,
            api_key=self._config.api_key,
            base_url=self._config.base_url,
        )

    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        llm = ChatOpenAI(
            model=model_name,
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        result = llm.invoke(request.messages)
        return ChatResponse(
            content=result.content,
            model=model_name,
        )

    def stream(self, request: ChatRequest, model_name: str) -> Iterator[str]:
        llm = ChatOpenAI(
            model=model_name,
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            streaming=True,
        )
        for chunk in llm.stream(request.messages):
            if isinstance(chunk.content, str) and chunk.content:
                yield chunk.content
