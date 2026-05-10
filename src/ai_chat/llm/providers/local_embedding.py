"""本地嵌入模型策略 — 基于 sentence-transformers。"""

from ..factory import register_embedding
from ..models import EmbeddingProvider, ProviderConfig


@register_embedding("local", lambda: ProviderConfig())
class LocalEmbeddingProvider(EmbeddingProvider):
    """本地嵌入提供商策略（无需 API，模型在本地运行）。

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

    def __init__(self, config: ProviderConfig | None = None) -> None:
        self._config = config or ProviderConfig()

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.SUPPORTED_MODELS

    def get_supported_models(self) -> list[str]:
        return list(self.SUPPORTED_MODELS)

    def _build_client(self, model_name: str):
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError:
            raise ImportError(
                "本地嵌入需要安装 sentence-transformers：\n"
                "  uv add sentence-transformers"
            ) from None
        return HuggingFaceEmbeddings(model_name=model_name)

    def embed(self, text: str, model_name: str) -> list[float]:
        client = self._build_client(model_name)
        return client.embed_query(text)

    def embed_batch(self, texts: list[str], model_name: str) -> list[list[float]]:
        client = self._build_client(model_name)
        return client.embed_documents(texts)
