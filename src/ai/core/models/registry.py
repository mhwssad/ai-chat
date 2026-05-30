"""工厂注册中心 — 工厂的工厂。

``ModelFactoryRegistry`` 通过 ``(model_type, backend)`` 二元组
统一调度所有模型工厂，扩展新模型类型只需 ``register_factory``。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, overload

from src.ai.exception.llm_exception import LLMException

if TYPE_CHECKING:
    from src.ai.core.models.base import (
        ChatModelBuilder,
        EmbeddingModelBuilder,
        ModelBuilder,
        ModelFactory,
    )


class ModelFactoryRegistry:
    """模型工厂注册中心 — 工厂的工厂。

    统一管理各类型模型工厂，通过 ``(model_type, backend)`` 二元组
    定位到具体的构建器。

    扩展方式：``registry.register_factory("rerank", RerankFactory())``
    无需修改任何已有代码（开闭原则）。

    示例::

        registry = ModelFactoryRegistry()
        builder = registry.get_builder("chat", "openai")
        llm = builder.build(config)
    """

    def __init__(self) -> None:
        self._factories: dict[str, ModelFactory] = {}

    # ── 工厂管理（对扩展开放） ──

    def register_factory(self, model_type: str, factory: ModelFactory) -> None:
        """注册模型工厂。扩展新模型类型只需此一步。"""
        self._factories[model_type] = factory

    def get_factory(self, model_type: str) -> ModelFactory:
        """获取模型工厂。

        :raises LLMException: 模型类型未注册时抛出。
        """
        factory = self._factories.get(model_type)
        if factory is None:
            raise LLMException(
                f"未注册的模型类型: {model_type!r}，可用: {self.list_model_types()}"
            )
        return factory

    def list_model_types(self) -> list[str]:
        """返回所有已注册的模型类型。"""
        return list(self._factories.keys())

    # ── 统一调度（对修改关闭：不依赖具体工厂类型） ──

    @overload
    def get_builder(
        self, model_type: Literal["chat"], backend: str
    ) -> ChatModelBuilder: ...

    @overload
    def get_builder(
        self, model_type: Literal["embedding"], backend: str
    ) -> EmbeddingModelBuilder: ...

    def get_builder(self, model_type: str, backend: str) -> ModelBuilder:
        """根据 (模型类型, 后端) 获取构建器。

        统一调用 ``factory.create_builder(backend)``，无需 isinstance。
        """
        return self.get_factory(model_type).create_builder(backend)

    @property
    def chat(self) -> ChatModelFactory:
        """快捷访问 Chat 工厂。"""
        return self.get_factory("chat")  # type: ignore[return-value]

    @property
    def embedding(self) -> EmbeddingModelFactory:
        """快捷访问 Embedding 工厂。"""
        return self.get_factory("embedding")  # type: ignore[return-value]
