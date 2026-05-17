"""Ollama 本地聊天模型策略。"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from src.ai_chat.config import settings
from src.ai_chat.llm.factory import register_chat
from src.ai_chat.llm.models import ProviderConfig
from src.ai_chat.llm.providers.chat.base import ChatProvider


@register_chat(
    "ollama",
    lambda: ProviderConfig(
        base_url=settings.ollama_base_url,
    ),
    requires_key=False,
)
class OllamaProvider(ChatProvider):
    """Ollama 本地聊天提供商策略。"""

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

    def _build_client(self, model_name: str, **kwargs) -> BaseChatModel:
        """构建 Ollama LangChain 客户端。Ollama 使用 num_predict 参数名。"""
        return ChatOllama(
            model=model_name,
            base_url=self._config.base_url,
            temperature=kwargs.get("temperature"),
            num_predict=kwargs.get("max_tokens"),
            stop=kwargs.get("stop"),
            timeout=self._config.timeout,
        )
