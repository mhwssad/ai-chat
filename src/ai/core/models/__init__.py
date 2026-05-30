"""模型构建模块。

通过泛型抽象工厂 + 策略 + 工厂方法构建 LangChain 模型实例（BaseChatModel / Embeddings）。
不负责请求发送、消息转换或工具绑定。

``ModelService`` 是统一的门面入口，外部通过它获取模型实例：

示例::

    from src.ai.core.models import ModelService

    model_service = container.model_container.model_service()
    llm = model_service.get_chat_llm(temperature=0.7)
    embeddings = model_service.get_embedding()

开闭原则：
- 新增后端：实现 ``ChatModelBuilder`` → ``chat_model_factory.register(MyBuilder)``
- 新增模型类型：新建 Builder ABC → 新建 Factory 子类 → ``model_registry.register_factory("rerank", factory)``
"""

from src.ai.core.models.base import (
    ChatModelBuilder,
    ConfigT,
    EmbeddingModelBuilder,
    ModelBuilder,
    ModelBuilderT,
    ModelFactory,
    ReturnT,
)
from src.ai.core.models.chat import (
    ChatModelFactory as ChatModelFactory,
    InitChatModelBuilder as InitChatModelBuilder,
)
from src.ai.core.models.embedding import (
    EmbeddingModelFactory as EmbeddingModelFactory,
    GoogleGenAIEmbeddingBuilder as GoogleGenAIEmbeddingBuilder,
    OllamaEmbeddingBuilder as OllamaEmbeddingBuilder,
    OpenAIEmbeddingBuilder as OpenAIEmbeddingBuilder,
)
from src.ai.core.models.registry import ModelFactoryRegistry
from src.ai.core.models.service import ModelService


# 惰性导入：DI 容器单例
def __getattr__(name: str):
    if name in ("model_registry", "model_service", "chat_model_factory", "embedding_model_factory"):
        from src.ai.core.container import container

        if name == "model_service":
            return container.model_container.model_service()
        reg = container.model_container.model_registry()
        if name == "model_registry":
            return reg
        if name == "chat_model_factory":
            return reg.chat
        if name == "embedding_model_factory":
            return reg.embedding
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ChatModelBuilder",
    "ChatModelFactory",
    "ConfigT",
    "EmbeddingModelBuilder",
    "EmbeddingModelFactory",
    "ModelBuilder",
    "ModelBuilderT",
    "ModelFactory",
    "ModelFactoryRegistry",
    "ModelService",
    "ReturnT",
    "chat_model_factory",
    "embedding_model_factory",
    "model_registry",
    "model_service",
]
