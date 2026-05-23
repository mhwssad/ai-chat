"""RAG embedding 生成。"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from src.ai.core.models import EmbeddingRequest, ModelClient
from src.ai.exception.base_exception import BaseExceptions


class RagEmbeddingError(BaseExceptions):
    """RAG embedding 失败。"""


@dataclass(frozen=True)
class EmbeddingResult:
    vectors: list[list[float]]
    model_name: str


class RagEmbeddingService:
    """优先复用 core/models，失败时回退到本地 hash embedding。"""

    def __init__(
        self,
        *,
        model_client: ModelClient | None = None,
        fallback_dimension: int = 384,
    ) -> None:
        self._model_client = model_client or ModelClient()
        self._fallback = HashEmbeddingProvider(dimension=fallback_dimension)

    def embed_texts(
        self,
        texts: list[str],
        *,
        model_id: int | None = None,
        provider_key: str | None = None,
        model_key: str | None = None,
        allow_fallback: bool = True,
    ) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(vectors=[], model_name="none")

        if model_id is not None or (provider_key and model_key):
            response = self._model_client.embedding(
                EmbeddingRequest(
                    texts=texts,
                    model_id=model_id,
                    provider_key=provider_key,
                    model_key=model_key,
                )
            )
            return EmbeddingResult(vectors=response.content, model_name=response.model)

        if not allow_fallback:
            raise RagEmbeddingError("未指定 embedding 模型")
        return EmbeddingResult(
            vectors=[self._fallback.embed(text) for text in texts],
            model_name=self._fallback.model_name,
        )


class HashEmbeddingProvider:
    """确定性本地 fallback embedding，便于无外部模型时跑通 RAG 链路。"""

    model_name = "local-hash-embedding"

    def __init__(self, *, dimension: int = 384) -> None:
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        words = text.lower().split()
        if not words:
            words = [text.lower()]
        for word in words:
            digest = hashlib.sha256(word.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

