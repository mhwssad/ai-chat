"""模型构建模块。

通过泛型抽象工厂 + 策略 + 工厂方法构建模型实例。
不负责请求发送、消息转换或工具绑定。

``ModelService`` 是统一的门面入口，外部通过它获取模型实例：

示例::

    from src.ai.core.models import ModelService

    model_service = container.model_container.model_service()
    llm = model_service.get_chat_llm(temperature=0.7)
    embeddings = model_service.get_embedding()
    image_gen = model_service.get_image_generator()
    tts = model_service.get_speech_synthesizer()

开闭原则：
- 新增后端：实现 ``ChatModelBuilder`` → ``chat_model_factory.register(MyBuilder)``
- 新增模型类型：新建 Builder ABC → 新建 Factory 子类 → ``model_registry.register_factory("rerank", factory)``
"""

from src.ai.core.models.base import (
    ChatModelBuilder,
    ConfigT,
    EmbeddingModelBuilder,
    ImageModelBuilder,
    ModelBuilder,
    ModelBuilderT,
    ModelFactory,
    ReturnT,
    TTSModelBuilder,
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
from src.ai.core.models.image import (
    ImageGenerator,
    ImageModelFactory,
    LocalImageBuilder,
    OpenAIImageBuilder,
    StabilityAIImageBuilder,
)
from src.ai.core.models.registry import ModelFactoryRegistry
from src.ai.core.models.service import ModelService
from src.ai.core.models.tts import (
    EdgeTTSBuilder,
    LocalTTSBuilder,
    OpenAITTSBuilder,
    SpeechSynthesizer,
    TTSModelFactory,
)
from src.ai.core.models.types import AudioData, ImageData


__all__ = [
    "AudioData",
    "ChatModelBuilder",
    "ChatModelFactory",
    "ConfigT",
    "EdgeTTSBuilder",
    "EmbeddingModelBuilder",
    "EmbeddingModelFactory",
    "ImageData",
    "ImageGenerator",
    "ImageModelBuilder",
    "ImageModelFactory",
    "LocalImageBuilder",
    "LocalTTSBuilder",
    "ModelBuilder",
    "ModelBuilderT",
    "ModelFactory",
    "ModelFactoryRegistry",
    "ModelService",
    "OpenAIImageBuilder",
    "OpenAITTSBuilder",
    "ReturnT",
    "SpeechSynthesizer",
    "StabilityAIImageBuilder",
    "TTSModelBuilder",
    "TTSModelFactory",
]
