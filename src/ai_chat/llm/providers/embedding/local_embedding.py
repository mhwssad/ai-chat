"""本地嵌入模型策略 — 基于 sentence-transformers。"""

from typing import Optional

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.factory import register_embedding
from src.ai_chat.llm.models import ProviderConfig
from src.ai_chat.llm.providers.embedding.base import EmbeddingProvider

logger = get_logger(__name__)


@register_embedding("local", lambda: ProviderConfig(), requires_key=False)
class LocalEmbeddingProvider(EmbeddingProvider):
    """本地嵌入提供商策略（无需 API，模型在本地运行）。

    使用 HuggingFace sentence-transformers 模型进行本地文本嵌入。
    首次使用时会自动从 HuggingFace Hub 下载模型权重。

    支持模型即 HuggingFace Hub 上的 sentence-transformer 模型名称：
    - all-MiniLM-L6-v2     (384 维，轻量快速)
    - all-mpnet-base-v2     (768 维，质量最佳)
    - bge-small-zh-v1.5     (512 维，中文优化)
    - bge-base-zh-v1.5      (768 维，中文优化)

    依赖：``pip install sentence-transformers``（首次使用时自动下载模型）。
    """

    SUPPORTED_MODELS = [
        "all-MiniLM-L6-v2",
        "all-mpnet-base-v2",
        "bge-small-zh-v1.5",
        "bge-base-zh-v1.5",
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()
        logger.debug("LocalEmbeddingProvider 初始化完成（无需远程 API）")

    def _build_client(self, model_name: str):
        """构建本地 HuggingFace Embeddings 客户端实例。

        延迟导入 sentence-transformers 依赖，仅在首次调用时检查安装状态。

        Args:
            model_name: HuggingFace 模型名称

        Returns:
            HuggingFaceEmbeddings 实例

        Raises:
            ImportError: sentence-transformers 未安装时抛出
        """
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError:
            logger.error("本地嵌入需要安装 sentence-transformers，但导入失败")
            raise ImportError(
                "本地嵌入需要安装 sentence-transformers：\n"
                "  uv add sentence-transformers"
            ) from None
        logger.debug("构建本地 Embeddings 客户端: model=%s", model_name)
        return HuggingFaceEmbeddings(model_name=model_name)

    def embed(self, text: str, model_name: str) -> list[float]:
        """对单段文本进行本地嵌入向量化。"""
        logger.info("本地嵌入请求: model=%s, 文本长度=%d", model_name, len(text))
        client = self._build_client(model_name)
        result = client.embed_query(text)
        logger.debug("本地嵌入完成: model=%s, 向量维度=%d", model_name, len(result))
        return result

    def embed_batch(self, texts: list[str], model_name: str) -> list[list[float]]:
        """批量嵌入多段文本。"""
        logger.info("本地批量嵌入请求: model=%s, 文本数量=%d", model_name, len(texts))
        client = self._build_client(model_name)
        results = client.embed_documents(texts)
        logger.debug("本地批量嵌入完成: model=%s, 结果数量=%d", model_name, len(results))
        return results
