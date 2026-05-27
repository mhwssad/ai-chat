"""模型构建器包。

按职责拆分为三个子模块：
- ``base`` — 策略接口（ChatModelBuilder / EmbeddingModelBuilder）+ 泛型抽象工厂
- ``chat`` — Chat 构建器 + ChatModelFactory
- ``embedding`` — Embedding 构建器 + EmbeddingModelFactory
- ``registry`` — 工厂注册中心 + 模块级单例

扩展方式（开闭原则）：
- 新增后端：实现 Builder → ``chat_model_factory.register(MyBuilder)``
- 新增模型类型：新建 Builder ABC + Factory 子类 → ``model_registry.register_factory(...)``
"""

from src.ai.core.models.builders.base import (
    ChatModelBuilder,
    ConfigT,
    EmbeddingModelBuilder,
    ModelBuilder,
    ModelBuilderT,
    ModelFactory,
    ReturnT,
)
from src.ai.core.models.builders.chat import ChatModelFactory, InitChatModelBuilder
from src.ai.core.models.builders.embedding import (
    EmbeddingModelFactory,
    GoogleGenAIEmbeddingBuilder,
    OllamaEmbeddingBuilder,
    OpenAIEmbeddingBuilder,
)
from src.ai.core.models.builders.registry import (
    ModelFactoryRegistry,
    chat_model_factory,
    embedding_model_factory,
    model_registry,
)

__all__ = [
    # base
    "ModelBuilder",
    "ModelBuilderT",
    "ModelFactory",
    "ConfigT",
    "ReturnT",
    "ChatModelBuilder",
    "EmbeddingModelBuilder",
    # chat
    "ChatModelFactory",
    "InitChatModelBuilder",
    # embedding
    "EmbeddingModelFactory",
    "OpenAIEmbeddingBuilder",
    "GoogleGenAIEmbeddingBuilder",
    "OllamaEmbeddingBuilder",
    # registry
    "ModelFactoryRegistry",
    "chat_model_factory",
    "embedding_model_factory",
    "model_registry",
]
