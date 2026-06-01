"""媒体生成相关异常。"""

from src.ai.exception.base_exception import BaseExceptions


class MediaGenerationException(BaseExceptions):
    """媒体生成基础异常。"""


class MediaNotFoundError(MediaGenerationException):
    """媒体文件不存在。"""


class ImageGenerationException(MediaGenerationException):
    """图像生成异常。"""


class TTSException(MediaGenerationException):
    """TTS 语音合成异常。"""
