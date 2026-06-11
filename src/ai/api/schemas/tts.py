"""TTS 相关请求/响应 Schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TtsSynthesizeRequest(BaseModel):
    """语音合成请求。"""

    text: str = Field(..., min_length=1, description="待合成文本")
    voice: str | None = Field(default=None, description="语音名称")
    speed: float | None = Field(default=None, gt=0, description="语速")
    output_format: str | None = Field(default=None, description="输出格式")


class TtsSynthesizeResponse(BaseModel):
    """语音合成响应。"""

    file: str = Field(description="保存的文件路径")
    audio_base64: str = Field(default="", description="Base64 编码音频")
    format: str = Field(description="音频格式")
    duration_seconds: float | None = Field(default=None, description="音频时长（秒）")


class AudioInfoResponse(BaseModel):
    """音频文件信息。"""

    filename: str = Field(description="文件名")
    path: str = Field(description="文件路径")
    size_bytes: int = Field(description="文件大小（字节）")
    format: str = Field(description="音频格式")
    created_at: str = Field(description="创建时间")
