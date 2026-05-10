"""Ollama 本地聊天模型策略。"""

from typing import Iterator, Optional

from langchain_ollama import ChatOllama

from src.ai_chat.config import settings
from ..factory import register_chat
from ..models import ChatProvider, ChatRequest, ChatResponse, ProviderConfig, extract_usage


@register_chat("ollama", lambda: ProviderConfig(
    base_url=settings.ollama_base_url,
))
class OllamaProvider(ChatProvider):
    """Ollama 本地聊天提供商策略。

    支持 Ollama 本地运行的所有模型，模型名称需与本地已拉取的模型一致。
    常见模型：qwen2.5, llama3.1, mistral, gemma2, deepseek-r1 …
    """

    SUPPORTED_MODELS = [
        "qwen2.5",
        "qwen2.5:7b",
        "qwen2.5:14b",
        "llama3.1",
        "llama3.1:8b",
        "llama3.1:70b",
        "mistral",
        "gemma2",
        "gemma2:9b",
        "deepseek-r1",
        "deepseek-r1:8b",
        "phi4",
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.SUPPORTED_MODELS

    def get_supported_models(self) -> list[str]:
        return list(self.SUPPORTED_MODELS)

    def get_client(self, model_name: str) -> ChatOllama:
        return ChatOllama(
            model=model_name,
            base_url=self._config.base_url,
        )

    def get_stream_client(self, model_name: str, *, temperature: float = 0.7, max_tokens: Optional[int] = None) -> ChatOllama:
        return ChatOllama(
            model=model_name,
            base_url=self._config.base_url,
            temperature=temperature,
            num_predict=max_tokens,
        )

    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        llm = ChatOllama(
            model=model_name,
            base_url=self._config.base_url,
            temperature=request.temperature,
            num_predict=request.max_tokens,
        )
        result = llm.invoke(request.messages)
        return ChatResponse(
            content=result.content,
            model=model_name,
            usage=extract_usage(result),
        )

    def stream(self, request: ChatRequest, model_name: str) -> Iterator[str]:
        llm = self.get_stream_client(model_name, temperature=request.temperature, max_tokens=request.max_tokens)
        for chunk in llm.stream(request.messages):
            if isinstance(chunk.content, str) and chunk.content:
                yield chunk.content
