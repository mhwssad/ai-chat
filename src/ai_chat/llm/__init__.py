"""LLM 模块入口 — 导出工厂、基类、模型和自动发现的供应商。"""

from .menu import menu_llm

from .base import ModelProvider
from .models import (
    ChatRequest,
    ChatResponse,
    LLMCircuitOpenError,
    LLMException,
    LLMRetryExhaustedError,
    ModelNotSupportedException,
    ProviderConfig,
    mask_key,
)

# factory 必须在 providers 之前加载，因为 auto-discovery 需要引用 register_chat/register_embedding
from .factory import llm_factory, register, register_chat, register_embedding

# 导入 providers 触发装饰器自动注册（同时触发 providers/__init__.py 的递归发现）
from . import providers as _providers

# 加载数据库中的外部模型到路由表
llm_factory._load_external_models()

# 将自动发现的 Provider 类重新导出
globals().update({k: v for k, v in _providers.__dict__.items() if isinstance(v, type)})

# ABC 从子目录延迟导入（在 factory 和 providers 都加载完成后）
from .providers.chat.base import ChatProvider
from .providers.embedding.base import EmbeddingProvider
from .providers.image.base import ImageProvider, ImageRequest, ImageResponse
from .providers.video.base import VideoProvider, VideoRequest, VideoResponse

# 可观测性
from .observability import (
    ErrorLogger,
    LLMUsageLog,
    UsageEntry,
    UsageTracker,
    error_logger,
    usage_tracker,
)

# 模型元数据与 token 工具
from .model_metadata import MODEL_CONTEXT_SIZES, get_model_context_size
from .model_config import model_config_store, ModelConfigStore, ModelConfigTable
from .token_utils import (
    count_text_tokens,
    estimate_message_tokens,
    estimate_messages_tokens,
    extract_prompt_tokens,
    extract_total_tokens,
)


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
    "LLMException",
    "LLMRetryExhaustedError",
    "LLMCircuitOpenError",
    # 配置
    "ProviderConfig",
    "mask_key",
    # 模型元数据
    "MODEL_CONTEXT_SIZES",
    "get_model_context_size",
    # token 工具
    "count_text_tokens",
    "estimate_message_tokens",
    "estimate_messages_tokens",
    "extract_prompt_tokens",
    "extract_total_tokens",
    # 可观测性
    "usage_tracker",
    "error_logger",
    "UsageTracker",
    "ErrorLogger",
    "UsageEntry",
    "LLMUsageLog",
    # 模型配置
    "model_config_store",
    "ModelConfigStore",
    "ModelConfigTable",
    # 菜单
    "menu_llm",
]
