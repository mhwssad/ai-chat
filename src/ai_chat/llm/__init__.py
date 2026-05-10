from .models import (
    ChatProvider,
    ChatRequest,
    ChatResponse,
    EmbeddingProvider,
    ModelNotSupportedException,
    ProviderConfig,
    mask_key,
)
from .factory import llm_factory, register_chat, register_embedding

# 导入 providers 触发装饰器自动注册
from . import providers as _providers

# 将自动发现的 Provider 类重新导出
globals().update(
    {k: v for k, v in _providers.__dict__.items() if isinstance(v, type)}
)



__all__ = [
    # 工厂
    "llm_factory",
    # 装饰器
    "register_chat",
    "register_embedding",
    # 聊天模型
    "ChatProvider",
    "ChatRequest",
    "ChatResponse",
    # 嵌入模型
    "EmbeddingProvider",
    # 异常
    "ModelNotSupportedException",
    # 配置
    "ProviderConfig",
    "mask_key",
]
