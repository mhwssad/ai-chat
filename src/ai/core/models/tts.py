"""TTS 语音合成模型构建器 + 工厂。

内置三种构建策略：OpenAI TTS / Edge TTS / 本地 TTS 服务。

扩展方式：实现 ``TTSModelBuilder`` 并注册到 ``tts_model_factory``。
"""

from __future__ import annotations

import io
from src.ai.config.logging_setup import get_logger
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from src.ai.core.models.base import ModelFactory, TTSModelBuilder
from src.ai.core.models.types import AudioData
from src.ai.exception.media_exception import TTSException

if TYPE_CHECKING:
    from src.ai.config.model_settings import TTSModelConfig

logger = get_logger(__name__)


# ── 语音合成器抽象 ──────────────────────────────────────


class SpeechSynthesizer(ABC):
    """语音合成器抽象接口。"""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        speed: float | None = None,
        output_format: str | None = None,
        **kwargs: Any,
    ) -> AudioData:
        """将文本合成为语音。

        Args:
            text: 待合成文本。
            voice: 语音名称/ID。
            speed: 语速（1.0 为正常速度）。
            output_format: 输出格式（如 "mp3", "wav"）。
            **kwargs: 后端特定参数。

        Returns:
            音频数据。
        """


# ── 私有实现 ────────────────────────────────────────────


class _OpenAITTSGenerator(SpeechSynthesizer):
    """OpenAI TTS 语音合成器。"""

    def __init__(self, client: Any, model_key: str) -> None:
        self._client = client
        self._model_key = model_key

    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        speed: float | None = None,
        output_format: str | None = None,
        **kwargs: Any,
    ) -> AudioData:
        try:
            params: dict[str, Any] = {
                "model": self._model_key,
                "input": text,
                "voice": voice or "alloy",
            }
            if speed is not None:
                params["speed"] = speed
            if output_format:
                params["response_format"] = output_format
            params.update(kwargs)

            response = await self._client.audio.speech.create(**params)
            audio_bytes = response.content

            fmt = output_format or "mp3"
            return AudioData(
                audio_bytes=audio_bytes,
                format=fmt,
                metadata={"model": self._model_key, "voice": voice or "alloy"},
            )
        except Exception as exc:
            raise TTSException(
                f"OpenAI TTS 合成失败: {exc}",
                context={"model": self._model_key, "text_length": len(text)},
            ) from exc


class _EdgeTTSGenerator(SpeechSynthesizer):
    """Edge TTS 语音合成器。"""

    def __init__(self) -> None:
        pass

    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        speed: float | None = None,
        output_format: str | None = None,
        **kwargs: Any,
    ) -> AudioData:
        try:
            import edge_tts

            voice_name = voice or "zh-CN-XiaoxiaoNeural"
            rate = f"+{int((speed - 1) * 100)}%" if speed and speed != 1.0 else "+0%"

            communicate = edge_tts.Communicate(text, voice_name, rate=rate)
            audio_buffer = io.BytesIO()

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])

            audio_bytes = audio_buffer.getvalue()
            fmt = output_format or "mp3"

            return AudioData(
                audio_bytes=audio_bytes,
                format=fmt,
                metadata={"provider": "edge_tts", "voice": voice_name},
            )
        except TTSException:
            raise
        except Exception as exc:
            raise TTSException(
                f"Edge TTS 合成失败: {exc}",
                context={"voice": voice, "text_length": len(text)},
            ) from exc


class _LocalTTSGenerator(SpeechSynthesizer):
    """本地 TTS 服务合成器。"""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        speed: float | None = None,
        output_format: str | None = None,
        **kwargs: Any,
    ) -> AudioData:
        from src.ai.utils.http.client import http_aclient

        try:
            params: dict[str, Any] = {"text": text}
            if voice:
                params["voice"] = voice
            if speed is not None:
                params["speed"] = speed
            if output_format:
                params["format"] = output_format
            params.update(kwargs)

            response = await http_aclient.post(
                f"{self._base_url}/tts",
                json=params,
                timeout=120,
            )

            fmt = output_format or "mp3"
            return AudioData(
                audio_bytes=response.content,
                format=fmt,
                metadata={"provider": "local_tts"},
            )
        except TTSException:
            raise
        except Exception as exc:
            raise TTSException(
                f"本地 TTS 合成失败: {exc}",
                context={"base_url": self._base_url, "text_length": len(text)},
            ) from exc


# ── 构建器 ──────────────────────────────────────────────


class OpenAITTSBuilder(TTSModelBuilder):
    """OpenAI TTS 构建策略。"""

    backend = ["openai"]

    def build(self, config: TTSModelConfig) -> _OpenAITTSGenerator:  # type: ignore[override]
        from openai import AsyncOpenAI

        client_kwargs: dict[str, Any] = {}
        if config.api_key:
            client_kwargs["api_key"] = config.api_key
        if config.base_url:
            client_kwargs["base_url"] = config.base_url

        client = AsyncOpenAI(**client_kwargs)
        return _OpenAITTSGenerator(client, config.model_key)


class EdgeTTSBuilder(TTSModelBuilder):
    """Edge TTS 构建策略。"""

    backend = ["edge_tts"]

    def build(self, config: TTSModelConfig) -> _EdgeTTSGenerator:  # type: ignore[override]
        return _EdgeTTSGenerator()


class LocalTTSBuilder(TTSModelBuilder):
    """本地 TTS 服务构建策略。"""

    backend = ["local_tts"]

    def build(self, config: TTSModelConfig) -> _LocalTTSGenerator:  # type: ignore[override]
        if not config.base_url:
            raise TTSException(
                "本地 TTS 需要配置 base_url",
                context={"backend": "local_tts"},
            )
        return _LocalTTSGenerator(base_url=config.base_url)


# ── TTS 工厂 ────────────────────────────────────────────


class TTSModelFactory(ModelFactory[TTSModelBuilder]):
    """TTS 语音合成模型工厂。"""

    def create_builder(self, backend: str) -> TTSModelBuilder:
        return self._resolve(backend, "TTS")
