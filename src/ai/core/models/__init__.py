"""模型构建模块。

通过泛型抽象工厂 + 策略 + 工厂方法构建 LangChain 模型实例（BaseChatModel / Embeddings）。
不负责请求发送、消息转换或工具绑定。

开闭原则：
- 新增后端：实现 ``ChatModelBuilder`` → ``chat_model_factory.register(MyBuilder)``
- 新增模型类型：新建 Builder ABC → 新建 Factory 子类 → ``model_registry.register_factory("rerank", factory)``

示例::

    from src.ai.core.models import model_registry, ChatModelConfig

    config = ChatModelConfig(model_key="gpt-4o", api_key="sk-...", base_url="https://api.openai.com/v1")
    builder = model_registry.get_builder("chat", "openai")
    llm = builder.build(config)
"""

from src.ai.core.models.builders import (
    ChatModelBuilder,
    ChatModelFactory,
    ConfigT,
    EmbeddingModelBuilder,
    EmbeddingModelFactory,
    ModelBuilder,
    ModelBuilderT,
    ModelFactory,
    ModelFactoryRegistry,
    ReturnT,
    chat_model_factory,
    embedding_model_factory,
    model_registry,
)
from src.ai.config.model_settings import ChatModelConfig, EmbeddingModelConfig

__all__ = [
    "ChatModelBuilder",
    "ChatModelConfig",
    "ChatModelFactory",
    "ConfigT",
    "EmbeddingModelBuilder",
    "EmbeddingModelConfig",
    "EmbeddingModelFactory",
    "ModelBuilder",
    "ModelBuilderT",
    "ModelFactory",
    "ModelFactoryRegistry",
    "ReturnT",
    "chat_model_factory",
    "embedding_model_factory",
    "model_registry",
]
