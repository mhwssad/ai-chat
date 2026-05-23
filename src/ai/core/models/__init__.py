"""通用多供应商多模型请求模块。"""

from src.ai.core.models.client import (
    ModelClient,
    create_embedding,
    create_chat_completion,
    create_chat_completion_stream,
)
from src.ai.core.models.defaults import install_default_providers
from src.ai.core.models.pricing import PricingCalculator
from src.ai.core.models.registry import (
    ModelProvider,
    ModelProviderRegistry,
    provider_registry,
    register_provider,
)
from src.ai.core.models.resolver import ModelResolver
from src.ai.core.models.telemetry import ModelTelemetryRecorder
from src.ai.core.models.tools import normalize_tools
from src.ai.core.models.types import (
    ChatMessage,
    ChatRequest,
    EmbeddingRequest,
    ModelCost,
    ModelRequest,
    ModelResponse,
    ModelStreamChunk,
    ModelUsage,
    ToolBinding,
)
from src.ai.core.models.usage import UsageCalculator

install_default_providers()

__all__ = [
    "ChatMessage",
    "ChatRequest",
    "ModelClient",
    "EmbeddingRequest",
    "ModelCost",
    "ModelProvider",
    "ModelProviderRegistry",
    "ModelRequest",
    "ModelResolver",
    "ModelResponse",
    "ModelStreamChunk",
    "ModelTelemetryRecorder",
    "ModelUsage",
    "PricingCalculator",
    "ToolBinding",
    "UsageCalculator",
    "create_chat_completion",
    "create_chat_completion_stream",
    "create_embedding",
    "install_default_providers",
    "normalize_tools",
    "provider_registry",
    "register_provider",
]
