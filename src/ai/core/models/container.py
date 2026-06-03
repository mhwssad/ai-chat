"""模型子系统 DI 容器。"""

from dependency_injector import containers, providers


def _create_model_registry():
    """构建 ModelFactoryRegistry 并注册所有构建器。"""
    from src.ai.core.models.chat import ChatModelFactory, InitChatModelBuilder, AnthropicChatBuilder
    from src.ai.core.models.embedding import (
        EmbeddingModelFactory,
        GoogleGenAIEmbeddingBuilder,
        OllamaEmbeddingBuilder,
        OpenAIEmbeddingBuilder,
    )
    from src.ai.core.models.image import (
        ImageModelFactory,
        LocalImageBuilder,
        OpenAIImageBuilder,
        StabilityAIImageBuilder,
    )
    from src.ai.core.models.registry import ModelFactoryRegistry
    from src.ai.core.models.tts import (
        EdgeTTSBuilder,
        LocalTTSBuilder,
        OpenAITTSBuilder,
        TTSModelFactory,
    )

    chat_factory = ChatModelFactory()
    chat_factory.register(InitChatModelBuilder)

    chat_factory.register(AnthropicChatBuilder)

    emb_factory = EmbeddingModelFactory()
    emb_factory.register_all(
        [
            OpenAIEmbeddingBuilder,
            GoogleGenAIEmbeddingBuilder,
            OllamaEmbeddingBuilder,
        ]
    )

    image_factory = ImageModelFactory()
    image_factory.register_all(
        [
            OpenAIImageBuilder,
            StabilityAIImageBuilder,
            LocalImageBuilder,
        ]
    )

    tts_factory = TTSModelFactory()
    tts_factory.register_all(
        [
            OpenAITTSBuilder,
            EdgeTTSBuilder,
            LocalTTSBuilder,
        ]
    )

    reg = ModelFactoryRegistry()
    reg.register_factory("chat", chat_factory)
    reg.register_factory("embedding", emb_factory)
    reg.register_factory("image", image_factory)
    reg.register_factory("tts", tts_factory)
    return reg


def _create_model_service(registry):
    """构建 ModelService 门面。"""
    from src.ai.config.model_settings import (
        ChatModelConfig,
        EmbeddingModelConfig,
        ImageModelConfig,
        TTSModelConfig,
    )
    from src.ai.core.models.service import ModelService

    return ModelService(
        registry=registry,
        chat_config=ChatModelConfig(),
        embedding_config=EmbeddingModelConfig(),
        image_config=ImageModelConfig(),
        tts_config=TTSModelConfig(),
    )


class ModelContainer(containers.DeclarativeContainer):
    """模型子系统容器。"""

    model_registry = providers.Singleton(_create_model_registry)
    model_service = providers.Singleton(
        _create_model_service,
        registry=model_registry,
    )
