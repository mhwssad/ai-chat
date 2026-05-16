"""视频生成模型提供商策略接口。"""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.base import ModelProvider

logger = get_logger(__name__)


@dataclass
class VideoRequest:
    """视频生成请求。

    Attributes:
        prompt: 视频生成的文本提示词
        duration: 目标视频时长（秒），None 时使用模型默认值
        resolution: 视频分辨率，如 '720p'、'1080p'
        extra: 供应商特有的额外参数
    """

    prompt: str
    duration: Optional[float] = None
    resolution: str = "720p"
    extra: dict = field(default_factory=dict)


@dataclass
class VideoResponse:
    """视频生成响应。

    Attributes:
        url: 生成的视频 URL
        model: 使用的模型名称
        duration: 实际视频时长（秒）
    """

    url: str
    model: str
    duration: Optional[float] = None


class VideoProvider(ModelProvider):
    """视频生成模型提供商策略。

    子类必须实现 generate 方法，对接具体的视频生成 API。
    """

    @property
    def provider_type(self) -> str:
        return "video"

    @abstractmethod
    def generate(self, request: VideoRequest, model_name: str) -> VideoResponse:
        """根据文本提示生成视频。

        Args:
            request: 视频生成请求对象
            model_name: 视频生成模型名称

        Returns:
            包含生成视频 URL 的 VideoResponse
        """
