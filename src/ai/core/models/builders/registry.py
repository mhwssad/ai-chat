"""工厂注册中心 — 工厂的工厂。

``ModelFactoryRegistry`` 通过 ``(model_type, backend)`` 二元组
统一调度所有模型工厂，扩展新模型类型只需 ``register_factory``。

模块末尾创建带内置构建器的单例，供全局使用。
"""

from typing import Literal, overload

from src.ai.core.models.builders.base import (
    ChatModelBuilder,
    EmbeddingModelBuilder,
    ModelBuilder,
    ModelFactory,
)
from src.ai.core.models.builders.chat import ChatModelFactory, InitChatModelBuilder
from src.ai.core.models.builders.embedding import (
    EmbeddingModelFactory,
    GoogleGenAIEmbeddingBuilder,
    OllamaEmbeddingBuilder,
    OpenAIEmbeddingBuilder,
)
from src.ai.exception.llm_exception import LLMException


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
            raise LLMException(f"未注册的模型类型: {model_type!r}，可用: {self.list_model_types()}")
        return factory

    def list_model_types(self) -> list[str]:
        """返回所有已注册的模型类型。"""
        return list(self._factories.keys())

    # ── 统一调度（对修改关闭：不依赖具体工厂类型） ──

    @overload
    def get_builder(self, model_type: Literal["chat"], backend: str) -> ChatModelBuilder: ...

    @overload
    def get_builder(self, model_type: Literal["embedding"], backend: str) -> EmbeddingModelBuilder: ...

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


# ── 模块级单例（带内置构建器） ──────────────────────────

chat_model_factory = ChatModelFactory()
chat_model_factory.register(InitChatModelBuilder)

embedding_model_factory = EmbeddingModelFactory()
embedding_model_factory.register_all([
    OpenAIEmbeddingBuilder,
    GoogleGenAIEmbeddingBuilder,
    OllamaEmbeddingBuilder,
])

model_registry = ModelFactoryRegistry()
model_registry.register_factory("chat", chat_model_factory)
model_registry.register_factory("embedding", embedding_model_factory)

if __name__ == '__main__':
    from src.ai.config.model_settings import chat_model_config, embedding_model_config
    from langchain_core.language_models import BaseChatModel
    from langchain_core.embeddings import Embeddings

    builder = model_registry.get_builder("chat", chat_model_config.backend)
    em_builder = model_registry.get_builder("embedding", embedding_model_config.backend)
    ai_model: BaseChatModel = builder.build(chat_model_config)
    em_model: Embeddings = em_builder.build(embedding_model_config)
    con = ai_model.invoke("你好")
    em = em_model.embed_query("你好")
    print(con)
    print(em)
