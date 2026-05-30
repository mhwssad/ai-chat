"""模型服务门面 — 统一的模型获取入口。

封装 ModelFactoryRegistry + Config 的创建逻辑，
外部只需调用 ``get_chat_llm()`` / ``get_embedding()`` 即可获取模型实例。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.language_models import BaseChatModel

    from src.ai.config.model_settings import ChatModelConfig, EmbeddingModelConfig
    from src.ai.core.models.registry import ModelFactoryRegistry


class ModelService:
    """模型服务门面。

    将模型创建的完整流程（Config → Registry → Builder → 实例）
    封装为简单的方法调用，外部不再需要了解内部工厂细节。

    示例::

        model_service = container.model_container.model_service()
        llm = model_service.get_chat_llm(temperature=0.7)
        embeddings = model_service.get_embedding()
    """

    def __init__(
        self,
        *,
        registry: ModelFactoryRegistry,
        chat_config: ChatModelConfig,
        embedding_config: EmbeddingModelConfig,
    ) -> None:
        self._registry = registry
        self._chat_config = chat_config
        self._embedding_config = embedding_config

    def get_chat_llm(
        self,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        streaming: bool = False,
    ) -> BaseChatModel:
        """获取 Chat LLM 实例。

        使用 chat_config 中的 backend 自动定位 Builder 并构建实例。

        Args:
            temperature: 温度参数。
            max_tokens: 最大输出 token 数。
            streaming: 是否启用流式。

        Returns:
            BaseChatModel 实例。
        """
        builder = self._registry.get_builder("chat", self._chat_config.backend)
        return builder.build(
            self._chat_config,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
        )

    def get_embedding(self) -> Embeddings:
        """获取 Embedding 实例。

        使用 embedding_config 中的 backend 自动定位 Builder 并构建实例。

        Returns:
            Embeddings 实例。
        """
        builder = self._registry.get_builder(
            "embedding", self._embedding_config.backend
        )
        return builder.build(self._embedding_config)

    @property
    def registry(self) -> ModelFactoryRegistry:
        """暴露注册表（供扩展注册新 builder）。"""
        return self._registry

    @property
    def chat_config(self) -> ChatModelConfig:
        """暴露 Chat 配置（供需要读取配置的场景使用）。"""
        return self._chat_config

    @property
    def embedding_config(self) -> EmbeddingModelConfig:
        """暴露 Embedding 配置。"""
        return self._embedding_config
