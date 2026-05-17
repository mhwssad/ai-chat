"""所有模型提供商的公共基类。"""

from abc import ABC, abstractmethod
from typing import ClassVar

from src.ai_chat.config.logging_setup import get_logger

logger = get_logger(__name__)


class ModelProvider(ABC):
    """模型提供商策略的公共基类。

    所有具体提供商（聊天、嵌入、图片、视频等）均继承此类。
    子类须设置 SUPPORTED_MODELS 列表和 provider_type 属性。

    设计模式：策略模式，每个具体 Provider 封装一个供应商的 API 细节，
    上层调用方通过统一的接口访问不同供应商。
    """

    SUPPORTED_MODELS: ClassVar[list[str]] = []

    @property
    @abstractmethod
    def provider_type(self) -> str:
        """返回提供商类别标识，如 'chat'、'embedding'、'image'、'video'。"""

    def supports_model(self, model_name: str) -> bool:
        """判断该策略是否支持给定的模型名称。"""
        supported = model_name in self.SUPPORTED_MODELS
        logger.debug(
            "[%s] 模型 '%s' 支持检查: %s", self.provider_type, model_name, supported
        )
        return supported

    def get_supported_models(self) -> list[str]:
        """返回该策略支持的所有模型名称列表（副本，防止外部修改）。"""
        return list(self.SUPPORTED_MODELS)
