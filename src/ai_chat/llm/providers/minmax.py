from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.ai_chat.config import settings
from src.ai_chat.llm.models import ChatProvider, ChatRequest, ChatResponse, extract_usage, ProviderConfig


class MinMaxProvider(ChatProvider):
    """
    minmax 提供商策略。
    """
    SUPPORTED_MODELS = [
        "minmax-2.7",
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()

    def get_client(self, model_name: str) -> BaseChatModel:
        return ChatOpenAI(
            model=model_name,
            api_key=settings.get_key(settings.openai_api_key),
            base_url=settings.api_key,
        )

    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        llm = ChatOpenAI(
            model=model_name,
            api_key=settings.get_key(settings.openai_api_key),
            base_url=settings.openai_base_url or None,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        result = llm.invoke(request.messages)
        return ChatResponse(
            content=result.content,
            model=model_name,
        )

    def get_supported_models(self) -> list[str]:
        return list(self.SUPPORTED_MODELS)

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.SUPPORTED_MODELS



