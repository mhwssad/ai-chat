"""图片生成模型提供商策略接口。"""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.base import ModelProvider

logger = get_logger(__name__)


@dataclass
class ImageRequest:
    """图片生成请求。

    Attributes:
        prompt: 图片生成的文本提示词
        size: 图片尺寸，如 '1024x1024'、'512x512'
        quality: 图片质量，如 'standard'、'hd'
        n: 一次生成的图片数量
        extra: 供应商特有的额外参数
    """

    prompt: str
    size: str = "1024x1024"
    quality: str = "standard"
    n: int = 1
    extra: dict = field(default_factory=dict)


@dataclass
class ImageResponse:
    """图片生成响应。

    Attributes:
        urls: 生成的图片 URL 列表
        model: 使用的模型名称
        revised_prompt: 模型修订后的提示词（部分供应商会返回）
    """

    urls: list[str]
    model: str
    revised_prompt: Optional[str] = None


class ImageProvider(ModelProvider):
    """图片生成模型提供商策略。

    子类必须实现 generate 方法，对接具体的图片生成 API。
    """

    @property
    def provider_type(self) -> str:
        return "image"

    @abstractmethod
    def generate(self, request: ImageRequest, model_name: str) -> ImageResponse:
        """根据文本提示生成图片。

        Args:
            request: 图片生成请求对象
            model_name: 图片生成模型名称

        Returns:
            包含生成图片 URL 的 ImageResponse
        """
