from .base import ModelProvider
from .models import (
    ChatRequest,
    ChatResponse,
    ModelNotSupportedException,
    ProviderConfig,
    mask_key,
)
# factory 必须在 providers 之前加载，因为 auto-discovery 需要引用 register_chat/register_embedding
from .factory import llm_factory, register, register_chat, register_embedding

# 导入 providers 触发装饰器自动注册（同时触发 providers/__init__.py 的递归发现）
from . import providers as _providers

# 将自动发现的 Provider 类重新导出
globals().update(
    {k: v for k, v in _providers.__dict__.items() if isinstance(v, type)}
)

# ABC 从子目录延迟导入（在 factory 和 providers 都加载完成后）
from .providers.chat.base import ChatProvider
from .providers.embedding.base import EmbeddingProvider
from .providers.image.base import ImageProvider, ImageRequest, ImageResponse
from .providers.video.base import VideoProvider, VideoRequest, VideoResponse


__all__ = [
    # 工厂
    "llm_factory",
    # 泛型装饰器
    "register",
    # 向后兼容装饰器
    "register_chat",
    "register_embedding",
    # 基类
    "ModelProvider",
    # 聊天模型
    "ChatProvider",
    "ChatRequest",
    "ChatResponse",
    # 嵌入模型
    "EmbeddingProvider",
    # 图片模型
    "ImageProvider",
    "ImageRequest",
    "ImageResponse",
    # 视频模型
    "VideoProvider",
    "VideoRequest",
    "VideoResponse",
    # 异常
    "ModelNotSupportedException",
    # 配置
    "ProviderConfig",
    "mask_key",
]
