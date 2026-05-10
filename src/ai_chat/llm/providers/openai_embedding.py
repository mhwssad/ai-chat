"""OpenAI 嵌入模型策略。"""

from typing import Optional

from langchain_openai import OpenAIEmbeddings

from src.ai_chat.config import settings
from ..factory import register_embedding
from ..models import EmbeddingProvider, ProviderConfig


@register_embedding("openai_emb", lambda: ProviderConfig(
    api_key=settings.get_key(settings.openai_api_key),
    base_url=settings.openai_base_url or None,
))
class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI 嵌入提供商策略。

    支持模型：text-embedding-ada-002, text-embedding-3-small, text-embedding-3-large。
    """

    SUPPORTED_MODELS = [
        "text-embedding-ada-002",
        "text-embedding-3-small",
        "text-embedding-3-large",
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.SUPPORTED_MODELS

    def get_supported_models(self) -> list[str]:
        return list(self.SUPPORTED_MODELS)

    def _build_client(self, model_name: str) -> OpenAIEmbeddings:
        return OpenAIEmbeddings(
            model=model_name,
            openai_api_key=self._config.api_key,
            openai_api_base=self._config.base_url,
        )

    def embed(self, text: str, model_name: str) -> list[float]:
        client = self._build_client(model_name)
        return client.embed_query(text)

    def embed_batch(self, texts: list[str], model_name: str) -> list[list[float]]:
        client = self._build_client(model_name)
        return client.embed_documents(texts)
