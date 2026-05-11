"""Minmax 聊天模型策略。"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.ai_chat.config import settings
from ..factory import register_chat
from ..models import ChatProvider, ChatRequest, ChatResponse, ProviderConfig
from typing import Iterator


@register_chat("qwen", lambda: ProviderConfig(
    api_key=settings.get_key(settings.qwen_api_key),
    base_url=settings.qwen_base_url,
))
class MinMaxProvider(ChatProvider):
    """Minmax 提供商策略。"""

    SUPPORTED_MODELS = [
        "qwen-turbo"
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.SUPPORTED_MODELS

    def get_supported_models(self) -> list[str]:
        return list(self.SUPPORTED_MODELS)

    def get_client(self, model_name: str) -> BaseChatModel:
        return ChatOpenAI(
            model=model_name,
            api_key=self._config.api_key,
            base_url=self._config.base_url,
        )

    def get_stream_client(self, model_name: str, *, temperature: float = 0.7, max_tokens: Optional[int] = None) -> BaseChatModel:
        return ChatOpenAI(
            model=model_name,
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            streaming=True,
        )

    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        llm = ChatOpenAI(
            model=model_name,
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            temperature=request.temperature,
            max_completion_tokens=request.max_tokens,
        )
        result = llm.invoke(request.messages)
        return ChatResponse(
            content=result.content,
            model=model_name,
        )

    def stream(self, request: ChatRequest, model_name: str) -> Iterator[str]:
        llm = self.get_stream_client(model_name, temperature=request.temperature, max_tokens=request.max_tokens)
        for chunk in llm.stream(request.messages):
            if isinstance(chunk.content, str) and chunk.content:
                yield chunk.content
