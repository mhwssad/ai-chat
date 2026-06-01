"""模型子系统通用数据类型。

定义图像生成和 TTS 语音合成的返回数据类。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ImageData:
    """图像生成结果。

    Attributes:
        image_bytes: 图像二进制数据。
        format: 图像格式（如 "png", "jpeg", "webp"）。
        revised_prompt: 模型修订后的提示词（若后端支持）。
        metadata: 附加元数据（seed、finish_reason 等）。
    """

    image_bytes: bytes
    format: str = "png"
    revised_prompt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AudioData:
    """TTS 语音合成结果。

    Attributes:
        audio_bytes: 音频二进制数据。
        format: 音频格式（如 "mp3", "wav", "opus"）。
        duration_seconds: 音频时长（秒），若后端不提供则为 None。
        metadata: 附加元数据。
    """

    audio_bytes: bytes
    format: str = "mp3"
    duration_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
