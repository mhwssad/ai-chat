"""OpenAI 嵌入模型策略。"""

from typing import Optional

from langchain_openai import OpenAIEmbeddings

from src.ai_chat.config import settings
from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.factory import register_embedding
from src.ai_chat.llm.models import ProviderConfig
from src.ai_chat.llm.providers.embedding.base import EmbeddingProvider

logger = get_logger(__name__)


@register_embedding(
    "openai_emb",
    lambda: ProviderConfig(
        api_key=settings.get_key(settings.openai_api_key),
        base_url=settings.openai_base_url or None,
    ),
)
class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI 嵌入提供商策略。

    通过 langchain-openai 包对接 OpenAI Embeddings API，
    支持自定义 base_url 以兼容其他 OpenAI 兼容的嵌入服务。

    支持模型：text-embedding-ada-002, text-embedding-3-small, text-embedding-3-large。
    """

    SUPPORTED_MODELS = [
        "text-embedding-ada-002",
        "text-embedding-3-small",
        "text-embedding-3-large",
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()
        logger.debug(
            "OpenAIEmbeddingProvider 初始化完成，base_url=%s",
            self._config.base_url or "<默认>",
        )

    def _build_client(self, model_name: str) -> OpenAIEmbeddings:
        """构建 OpenAI Embeddings 客户端实例。

        Args:
            model_name: 嵌入模型名称

        Returns:
            配置好的 OpenAIEmbeddings 实例
        """
        logger.debug("构建 OpenAI Embeddings 客户端: model=%s", model_name)
        return OpenAIEmbeddings(
            model=model_name,
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            timeout=self._config.timeout,
        )

    def embed(self, text: str, model_name: str) -> list[float]:
        """对单段文本进行嵌入向量化。"""
        logger.info("OpenAI 嵌入请求: model=%s, 文本长度=%d", model_name, len(text))
        client = self._build_client(model_name)
        result = client.embed_query(text)
        logger.debug("OpenAI 嵌入完成: model=%s, 向量维度=%d", model_name, len(result))
        return result

    def embed_batch(self, texts: list[str], model_name: str) -> list[list[float]]:
        """批量嵌入多段文本。"""
        logger.info(
            "OpenAI 批量嵌入请求: model=%s, 文本数量=%d", model_name, len(texts)
        )
        client = self._build_client(model_name)
        results = client.embed_documents(texts)
        logger.debug(
            "OpenAI 批量嵌入完成: model=%s, 结果数量=%d", model_name, len(results)
        )
        return results
