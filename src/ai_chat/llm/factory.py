"""抽象工厂 — 整合配置工厂、策略工厂与模型路由。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Generic, Optional, TypeVar

from src.ai_chat.llm.base import ModelProvider
from src.ai_chat.llm.models import (
    ChatRequest,
    ChatResponse,
    ModelNotSupportedException,
    ProviderConfig,
)

if TYPE_CHECKING:
    from src.ai_chat.llm.providers.chat.base import ChatProvider
    from src.ai_chat.llm.providers.embedding.base import EmbeddingProvider


# ======================================================================
# 配置工厂 — 按供应商名称创建 ProviderConfig
# ======================================================================

class ProviderConfigFactory:
    """通过供应商名称注册并创建 ProviderConfig。"""

    def __init__(self) -> None:
        self._registry: dict[str, Callable[[], ProviderConfig]] = {}

    def register(self, name: str, factory_fn: Callable[[], ProviderConfig]) -> None:
        """注册配置创建函数。"""
        self._registry[name] = factory_fn

    def create(self, name: str, **overrides) -> ProviderConfig:
        """根据供应商名称创建 ProviderConfig，支持字段覆盖。"""
        if name not in self._registry:
            raise KeyError(f"未注册的供应商配置：'{name}'，已注册：{list(self._registry)}")
        config = self._registry[name]()
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config


# ======================================================================
# 策略工厂 — 按供应商名称创建 Provider 实例
# ======================================================================

T = TypeVar("T")


class ProviderFactory(Generic[T]):
    """泛型策略工厂，按供应商名称创建 Provider 实例。"""

    def __init__(self) -> None:
        self._registry: dict[str, type[T]] = {}

    def register(self, name: str, cls: type[T]) -> None:
        """注册 Provider 类。"""
        self._registry[name] = cls

    def create(self, name: str, config: Optional[ProviderConfig] = None) -> T:
        """创建 Provider 实例。"""
        if name not in self._registry:
            raise KeyError(f"未注册的供应商：'{name}'，已注册：{list(self._registry)}")
        return self._registry[name](config)

    @property
    def registered_names(self) -> list[str]:
        return list(self._registry)


# ======================================================================
# 抽象工厂 — 泛型注册 + 模型路由
# ======================================================================

class LLMFactory:
    """抽象工厂，整合配置工厂、策略工厂与按模型名称路由。

    支持任意 provider_type（chat、embedding、image、video 等）的泛型注册。

    用法：
        llm_factory.register("chat", "gemini", GeminiProvider, lambda: ProviderConfig(...))
        llm_factory.get_provider("chat", "gemini-2.0-flash")
        # 向后兼容：
        llm_factory.get_chat_provider("gemini-2.0-flash")
    """

    def __init__(self) -> None:
        self.config_factory = ProviderConfigFactory()
        # provider_type -> ProviderFactory
        self._provider_factories: dict[str, ProviderFactory] = {}
        # provider_type -> {model_name: provider_name}
        self._routing: dict[str, dict[str, str]] = {}

    # ── 泛型注册 ─────────────────────────────────────────

    def register(
        self,
        provider_type: str,
        name: str,
        provider_cls: type[ModelProvider],
        config_fn: Callable[[], ProviderConfig],
        requires_key: bool = True,
    ) -> None:
        """泛型注册：按 provider_type 注册供应商的配置、策略类与模型路由。

        requires_key=True 时，提前调用 config_fn 检查 api_key，
        若为 None 则跳过注册（无可用密钥的供应商不会出现在路由表中）。
        """
        if requires_key:
            config = config_fn()
            if config.api_key is None:
                return
        if provider_type not in self._provider_factories:
            self._provider_factories[provider_type] = ProviderFactory()
            self._routing[provider_type] = {}
        self.config_factory.register(name, config_fn)
        self._provider_factories[provider_type].register(name, provider_cls)
        for model_name in getattr(provider_cls, "SUPPORTED_MODELS", []):
            self._routing[provider_type][model_name] = name

    def _get_provider(self, provider_type: str, model_name: str) -> ModelProvider:
        """按 provider_type 和 model_name 路由到对应的 Provider 实例。"""
        routing = self._routing.get(provider_type, {})
        provider_name = routing.get(model_name)
        if provider_name is None:
            raise ModelNotSupportedException(model_name, list(routing))
        config = self.config_factory.create(provider_name)
        return self._provider_factories[provider_type].create(provider_name, config)

    def get_provider(self, provider_type: str, model_name: str) -> ModelProvider:
        """公开的泛型 provider 查询。"""
        return self._get_provider(provider_type, model_name)

    def get_supported_models(self, provider_type: str) -> list[str]:
        """返回指定类型下所有已注册模型名称列表。"""
        return list(self._routing.get(provider_type, {}))

    # ── 向后兼容：chat ───────────────────────────────────

    def register_chat(
        self,
        name: str,
        provider_cls: type[ChatProvider],
        config_fn: Callable[[], ProviderConfig],
        requires_key: bool = True,
    ) -> None:
        """注册聊天供应商（向后兼容）。"""
        self.register("chat", name, provider_cls, config_fn, requires_key=requires_key)

    def create_chat_provider(
        self, name: str, config: Optional[ProviderConfig] = None
    ) -> ChatProvider:
        """按供应商名称创建聊天 Provider。"""
        if config is None:
            config = self.config_factory.create(name)
        return self._provider_factories["chat"].create(name, config)

    def get_chat_provider(self, model_name: str) -> ChatProvider:
        """根据模型名称路由到对应的聊天 Provider。"""
        return self._get_provider("chat", model_name)

    def get_stream_client(self, model_name: str, *, temperature: float = 0.7, max_tokens: Optional[int] = None):
        """根据模型名称路由，获取带流式配置的 LangChain 客户端。"""
        provider = self.get_chat_provider(model_name)
        return provider.get_stream_client(model_name, temperature=temperature, max_tokens=max_tokens)

    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        """根据模型名称自动路由，发起聊天请求。"""
        provider = self.get_chat_provider(model_name)
        return provider.chat(request, model_name)

    def stream(self, request: ChatRequest, model_name: str):
        """根据模型名称自动路由，流式聊天，逐 token 返回。"""
        provider = self.get_chat_provider(model_name)
        return provider.stream(request, model_name)

    def get_all_supported_chat_models(self) -> list[str]:
        """返回所有已注册聊天策略支持的模型名称列表。"""
        return list(self._routing.get("chat", {}))

    # ── 向后兼容：embedding ──────────────────────────────

    def register_embedding(
        self,
        name: str,
        provider_cls: type[EmbeddingProvider],
        config_fn: Callable[[], ProviderConfig],
        requires_key: bool = True,
    ) -> None:
        """注册嵌入供应商（向后兼容）。"""
        self.register("embedding", name, provider_cls, config_fn, requires_key=requires_key)

    def create_embedding_provider(
        self, name: str, config: Optional[ProviderConfig] = None
    ) -> EmbeddingProvider:
        """按供应商名称创建嵌入 Provider。"""
        if config is None:
            config = self.config_factory.create(name)
        return self._provider_factories["embedding"].create(name, config)

    def get_embedding_provider(self, model_name: str) -> EmbeddingProvider:
        """根据模型名称路由到对应的嵌入 Provider。"""
        return self._get_provider("embedding", model_name)

    def embed(self, text: str, model_name: str) -> list[float]:
        """根据模型名称自动路由，获取文本嵌入向量。"""
        provider = self.get_embedding_provider(model_name)
        return provider.embed(text, model_name)

    def embed_batch(self, texts: list[str], model_name: str) -> list[list[float]]:
        """根据模型名称自动路由，批量获取嵌入向量。"""
        provider = self.get_embedding_provider(model_name)
        return provider.embed_batch(texts, model_name)

    def get_all_supported_embedding_models(self) -> list[str]:
        """返回所有已注册嵌入策略支持的模型名称列表。"""
        return list(self._routing.get("embedding", {}))


# ======================================================================
# 装饰器 — 供应商自动注册
# ======================================================================

def register(provider_type: str, name: str, config_fn: Callable[[], ProviderConfig], *, requires_key: bool = True):
    """泛型类装饰器：将供应商自动注册到 llm_factory。

    requires_key=False 时跳过密钥检查，始终注册（如 Ollama、本地模型）。
    """
    def decorator(cls):
        llm_factory.register(provider_type, name, cls, config_fn, requires_key=requires_key)
        return cls
    return decorator


def register_chat(name: str, config_fn: Callable[[], ProviderConfig], *, requires_key: bool = True):
    """类装饰器：将聊天供应商自动注册到 llm_factory。

    用法::

        @register_chat("gemini", lambda: ProviderConfig(
            api_key=settings.get_key(settings.google_api_key),
        ))
        class GeminiProvider(ChatProvider):
            ...
    """
    return register("chat", name, config_fn, requires_key=requires_key)


def register_embedding(name: str, config_fn: Callable[[], ProviderConfig], *, requires_key: bool = True):
    """类装饰器：将嵌入供应商自动注册到 llm_factory。"""
    return register("embedding", name, config_fn, requires_key=requires_key)


# ======================================================================
# 全局单例
# ======================================================================

llm_factory = LLMFactory()
