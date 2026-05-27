"""RAG Embedding 回退 — 无外部模型时的确定性本地向量。

当 EmbeddingModelConfig.model_key 未配置时，HashEmbeddings 作为回退，
实现 LangChain Embeddings 接口，可直接传入 langchain-chroma。
"""

import hashlib
import math

from langchain_core.embeddings import Embeddings

from src.ai.config.settings import settings


class HashEmbeddings(Embeddings):
    """确定性本地 fallback embedding，实现 LangChain Embeddings 接口。

    基于 SHA-256 哈希生成固定维度向量，无需外部模型即可跑通 RAG 链路。
    """

    def __init__(self, dimension: int | None = None) -> None:
        self.dimension = dimension or settings.rag.rag_fallback_dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量 embed 文档文本。"""
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        """Embed 查询文本。"""
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        """确定性哈希 embedding：SHA-256 → 维度映射 → 累积 → L2 归一化。"""
        vector = [0.0] * self.dimension
        words = text.lower().split() or [text.lower()]
        for word in words:
            digest = hashlib.sha256(word.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]
