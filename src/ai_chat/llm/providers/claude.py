"""Anthropic Claude 聊天模型策略。"""

from langchain_anthropic import ChatAnthropic

from ai_chat.config import settings
from ai_chat.llm.models import ChatProvider, ChatRequest, ChatResponse, ProviderConfig, extract_usage


class ClaudeProvider(ChatProvider):
    """Anthropic Claude 提供商策略。

    支持模型：claude-sonnet-4-20250514, claude-3-5-sonnet-20241022, claude-3-opus-20240229 …
    """

    SUPPORTED_MODELS = [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "claude-3-haiku-20240307",
    ]

    def __init__(self, config: ProviderConfig | None = None) -> None:
        self._config = config or ProviderConfig()

    def _api_key(self):
        return self._config.api_key or settings.get_key(settings.anthropic_api_key)

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.SUPPORTED_MODELS

    def get_supported_models(self) -> list[str]:
        return list(self.SUPPORTED_MODELS)

    def get_client(self, model_name: str) -> ChatAnthropic:
        return ChatAnthropic(
            model=model_name,
            api_key=self._api_key(),
        )

    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        llm = ChatAnthropic(
            model=model_name,
            api_key=self._api_key(),
            temperature=request.temperature,
            max_tokens=request.max_tokens or 4096,
            timeout=self._config.timeout,
        )
        result = llm.invoke(request.messages)
        return ChatResponse(
            content=result.content,
            model=model_name,
            usage=extract_usage(result),
        )
