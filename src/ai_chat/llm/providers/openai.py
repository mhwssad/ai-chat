"""OpenAI 聊天模型策略。"""

from langchain_openai import ChatOpenAI

from src.ai_chat.config import settings
from src.ai_chat.llm.models import ChatProvider, ChatRequest, ChatResponse, extract_usage


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

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.SUPPORTED_MODELS

    def get_supported_models(self) -> list[str]:
        return list(self.SUPPORTED_MODELS)

    def get_client(self, model_name: str) -> ChatOpenAI:
        return ChatOpenAI(
            model=model_name,
            api_key=settings.get_key(settings.openai_api_key),
            base_url=settings.openai_base_url or None,
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
