"""模型服务门面 — 统一的模型获取入口。

封装 ModelFactoryRegistry + Config 的创建逻辑，
外部只需调用 ``get_chat_llm()`` / ``get_embedding()`` 即可获取模型实例。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.language_models import BaseChatModel

    from src.ai.config.model_settings import (
        ChatModelConfig,
        EmbeddingModelConfig,
        ImageModelConfig,
        TTSModelConfig,
    )
    from src.ai.core.models.image import ImageGenerator
    from src.ai.core.models.registry import ModelFactoryRegistry
    from src.ai.core.models.tts import SpeechSynthesizer


class ModelService:
    """模型服务门面。

    将模型创建的完整流程（Config → Registry → Builder → 实例）
    封装为简单的方法调用，外部不再需要了解内部工厂细节。

    示例::

        model_service = container.model_container.model_service()
        llm = model_service.get_chat_llm(temperature=0.7)
        embeddings = model_service.get_embedding()
        image_gen = model_service.get_image_generator()
        tts = model_service.get_speech_synthesizer()
    """

    def __init__(
        self,
        *,
        registry: ModelFactoryRegistry,
        chat_config: ChatModelConfig,
        embedding_config: EmbeddingModelConfig,
        image_config: ImageModelConfig | None = None,
        tts_config: TTSModelConfig | None = None,
    ) -> None:
        self._registry = registry
        self._chat_config = chat_config
        self._embedding_config = embedding_config
        self._image_config = image_config
        self._tts_config = tts_config

    def get_chat_llm(
        self,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        streaming: bool = False,
        enable_thinking: bool = False,
    ) -> BaseChatModel:
        """获取 Chat LLM 实例。

        使用 chat_config 中的 backend 自动定位 Builder 并构建实例。

        Args:
            temperature: 温度参数。
            max_tokens: 最大输出 token 数。
            streaming: 是否启用流式。
            enable_thinking: 是否启用深度思考（思维链）。

        Returns:
            BaseChatModel 实例。
        """
        builder = self._registry.get_builder("chat", self._chat_config.backend)
        return builder.build(
            self._chat_config,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
            enable_thinking=enable_thinking,
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

    def get_image_generator(self) -> ImageGenerator:
        """获取图像生成器实例。

        使用 image_config 中的 backend 自动定位 Builder 并构建实例。

        Returns:
            ImageGenerator 实例。

        Raises:
            LLMException: 未配置 image_config 时抛出。
        """
        if self._image_config is None:
            from src.ai.exception.llm_exception import LLMException

            raise LLMException("图像生成未配置，请设置 IMAGE_MODEL_* 环境变量")
        builder = self._registry.get_builder("image", self._image_config.backend)
        return builder.build(self._image_config)  # type: ignore[return-value]

    def get_speech_synthesizer(self) -> SpeechSynthesizer:
        """获取语音合成器实例。

        使用 tts_config 中的 backend 自动定位 Builder 并构建实例。

        Returns:
            SpeechSynthesizer 实例。

        Raises:
            LLMException: 未配置 tts_config 时抛出。
        """
        if self._tts_config is None:
            from src.ai.exception.llm_exception import LLMException

            raise LLMException("TTS 语音合成未配置，请设置 TTS_MODEL_* 环境变量")
        builder = self._registry.get_builder("tts", self._tts_config.backend)
        return builder.build(self._tts_config)  # type: ignore[return-value]

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

    @property
    def image_config(self) -> ImageModelConfig | None:
        """暴露 Image 配置。"""
        return self._image_config

    @property
    def tts_config(self) -> TTSModelConfig | None:
        """暴露 TTS 配置。"""
        return self._tts_config
