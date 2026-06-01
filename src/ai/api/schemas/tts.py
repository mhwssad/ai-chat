"""TTS API Schema 定义。"""

from datetime import datetime

from pydantic import BaseModel, Field


class TTSSynthesizeRequest(BaseModel):
    """TTS 语音合成请求。"""

    text: str = Field(description="待合成文本", min_length=1, max_length=4096)
    voice: str = Field(default="alloy", description="语音名称")
    speed: float = Field(
        default=1.0, description="语速，1.0 为正常速度", ge=0.25, le=4.0
    )
    output_format: str = Field(
        default="mp3", description="输出格式: mp3、opus、aac、flac、wav"
    )


class TTSSynthesizeResponse(BaseModel):
    """TTS 语音合成响应。"""

    file: str = Field(description="保存的文件路径")
    audio_base64: str = Field(description="Base64 编码的音频数据")
    format: str = Field(description="音频格式")
    duration_seconds: float | None = Field(default=None, description="音频时长（秒）")


class AudioMetaResponse(BaseModel):
    """音频元数据响应。"""

    filename: str = Field(description="文件名")
    size_bytes: int = Field(description="文件大小（字节）")
    format: str = Field(description="音频格式")
    created_at: datetime = Field(description="创建时间")
