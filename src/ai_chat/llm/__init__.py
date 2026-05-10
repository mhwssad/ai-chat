from .models import (
    ChatProvider,
    ChatRequest,
    ChatResponse,
    EmbeddingProvider,
    ModelNotSupportedException,
    ProviderConfig,
    mask_key,
)
from .factory import chat_factory, embedding_factory
from .providers import (
    OpenAIProvider,
    GeminiProvider,
    ClaudeProvider,
    OllamaProvider,
    OpenAIEmbeddingProvider,
    LocalEmbeddingProvider,
    OllamaEmbeddingProvider,
)

# 注册默认聊天策略
chat_factory.register_many([
    OpenAIProvider(),
    GeminiProvider(),
    ClaudeProvider(),
    OllamaProvider(),
])

# 注册默认嵌入策略
embedding_factory.register_many([
    OpenAIEmbeddingProvider(),
    LocalEmbeddingProvider(),
    OllamaEmbeddingProvider(),
])

__all__ = [
    # 聊天模型
    "chat_factory",
    "ChatProvider",
    "ChatRequest",
    "ChatResponse",
    # 嵌入模型
    "embedding_factory",
    "EmbeddingProvider",
    # 异常
    "ModelNotSupportedException",
    # 配置
    "ProviderConfig",
    "mask_key",
    # 聊天策略
    "OpenAIProvider",
    "GeminiProvider",
    "ClaudeProvider",
    "OllamaProvider",
    # 嵌入策略
    "OpenAIEmbeddingProvider",
    "LocalEmbeddingProvider",
    "OllamaEmbeddingProvider",
]
