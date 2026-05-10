"""Ollama 本地嵌入模型策略。"""

from typing import Optional

from langchain_ollama import OllamaEmbeddings

from ..factory import register_embedding
from ..models import EmbeddingProvider, ProviderConfig
from src.ai_chat.config import settings


@register_embedding("ollama_emb", lambda: ProviderConfig(
    base_url=settings.ollama_base_url,
))
class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama 本地嵌入提供商策略。

    支持 Ollama 中可用的嵌入模型，模型名称需与本地已拉取的模型一致。
    常见嵌入模型：nomic-embed-text, mxbai-embed-large, bge-m3, snowflake-arctic-embed …
    """

    SUPPORTED_MODELS = [
        "nomic-embed-text",
        "mxbai-embed-large",
        "bge-m3",
        "bge-m3:latest",
        "snowflake-arctic-embed",
        "all-minilm",
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.SUPPORTED_MODELS

    def get_supported_models(self) -> list[str]:
        return list(self.SUPPORTED_MODELS)

    def _build_client(self, model_name: str) -> OllamaEmbeddings:
        return OllamaEmbeddings(
            model=model_name,
            base_url=self._config.base_url,
        )

    def embed(self, text: str, model_name: str) -> list[float]:
        client = self._build_client(model_name)
        return client.embed_query(text)

    def embed_batch(self, texts: list[str], model_name: str) -> list[list[float]]:
        client = self._build_client(model_name)
        return client.embed_documents(texts)
