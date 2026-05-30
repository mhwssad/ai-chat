"""Embedding 模型构建器 + 工厂。

内置三种构建器：OpenAI / GoogleGenAI / Ollama。

扩展方式：实现 ``EmbeddingModelBuilder`` 并注册到 ``embedding_model_factory``。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.ai.core.models.base import EmbeddingModelBuilder, ModelFactory

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings

    from src.ai.config.model_settings import EmbeddingModelConfig


# ── 内置构建器 ─────────────────────────────────────────


class OpenAIEmbeddingBuilder(EmbeddingModelBuilder):
    """OpenAI Embedding 构建策略。"""

    backend = ["openai"]

    def build(self, config: EmbeddingModelConfig) -> Embeddings:
        from langchain_openai import OpenAIEmbeddings

        kwargs: dict = {"model": config.model_key}
        if config.api_key:
            kwargs["api_key"] = config.api_key
        if config.base_url:
            kwargs["base_url"] = config.base_url
        return OpenAIEmbeddings(**kwargs)


class GoogleGenAIEmbeddingBuilder(EmbeddingModelBuilder):
    """Google Generative AI Embedding 构建策略。"""

    backend = ["google_genai"]

    def build(self, config: EmbeddingModelConfig) -> Embeddings:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        kwargs: dict = {"model": config.model_key}
        if config.api_key:
            kwargs["google_api_key"] = config.api_key
        return GoogleGenerativeAIEmbeddings(**kwargs)


class OllamaEmbeddingBuilder(EmbeddingModelBuilder):
    """Ollama Embedding 构建策略。"""

    backend = ["ollama"]

    def build(self, config: EmbeddingModelConfig) -> Embeddings:
        from langchain_ollama import OllamaEmbeddings

        kwargs: dict = {"model": config.model_key}
        if config.base_url:
            kwargs["base_url"] = config.base_url
        return OllamaEmbeddings(**kwargs)


# ── Embedding 工厂 ─────────────────────────────────────


class EmbeddingModelFactory(ModelFactory[EmbeddingModelBuilder]):
    """Embedding 模型工厂。"""

    def create_builder(self, backend: str) -> EmbeddingModelBuilder:
        return self._resolve(backend, "Embedding")
