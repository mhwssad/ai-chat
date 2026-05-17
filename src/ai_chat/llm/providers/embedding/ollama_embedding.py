"""Ollama 本地嵌入模型策略。"""

from typing import Optional

from langchain_ollama import OllamaEmbeddings

from src.ai_chat.config import settings
from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.factory import register_embedding
from src.ai_chat.llm.models import ProviderConfig
from src.ai_chat.llm.providers.embedding.base import EmbeddingProvider

logger = get_logger(__name__)


@register_embedding(
    "ollama_emb",
    lambda: ProviderConfig(
        base_url=settings.ollama_base_url,
    ),
    requires_key=False,
)
class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama 本地嵌入提供商策略。

    通过 langchain-ollama 包对接本地 Ollama 嵌入服务。
    无需 API 密钥（requires_key=False），模型在本地运行。

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
        logger.debug(
            "OllamaEmbeddingProvider 初始化完成，base_url=%s", self._config.base_url
        )

    def _build_client(self, model_name: str) -> OllamaEmbeddings:
        """构建 Ollama Embeddings 客户端实例。

        Args:
            model_name: 嵌入模型名称

        Returns:
            配置好的 OllamaEmbeddings 实例
        """
        logger.debug("构建 Ollama Embeddings 客户端: model=%s", model_name)
        return OllamaEmbeddings(
            model=model_name,
            base_url=self._config.base_url,
            timeout=self._config.timeout,
        )

    def embed(self, text: str, model_name: str) -> list[float]:
        """对单段文本进行本地嵌入向量化。"""
        logger.info("Ollama 嵌入请求: model=%s, 文本长度=%d", model_name, len(text))
        client = self._build_client(model_name)
        result = client.embed_query(text)
        logger.debug("Ollama 嵌入完成: model=%s, 向量维度=%d", model_name, len(result))
        return result

    def embed_batch(self, texts: list[str], model_name: str) -> list[list[float]]:
        """批量嵌入多段文本。"""
        logger.info(
            "Ollama 批量嵌入请求: model=%s, 文本数量=%d", model_name, len(texts)
        )
        client = self._build_client(model_name)
        results = client.embed_documents(texts)
        logger.debug(
            "Ollama 批量嵌入完成: model=%s, 结果数量=%d", model_name, len(results)
        )
        return results
