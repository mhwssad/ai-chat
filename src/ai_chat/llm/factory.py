"""抽象工厂 — 整合配置工厂、策略工厂与模型路由。"""

from typing import Callable, Generic, Optional, TypeVar

from src.ai_chat.llm.models import (
    ChatProvider,
    ChatRequest,
    ChatResponse,
    EmbeddingProvider,
    ModelNotSupportedException,
    ProviderConfig,
)


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
# 抽象工厂 — 整合配置 + 策略 + 模型路由
# ======================================================================

class LLMFactory:
    """抽象工厂，整合配置工厂、策略工厂与按模型名称路由。

    用法：
        llm_factory.register_chat("gemini", GeminiProvider, lambda: ProviderConfig(...))
        llm_factory.create_chat_provider("gemini")              # 按供应商名
        llm_factory.get_chat_provider("gemini-2.0-flash")       # 按模型名路由
        llm_factory.chat(request, "gemini-2.0-flash")           # 路由 + 聊天
    """

    def __init__(self) -> None:
        self.config_factory = ProviderConfigFactory()
        self.chat_factory = ProviderFactory[ChatProvider]()
        self.embedding_factory = ProviderFactory[EmbeddingProvider]()
        self._chat_routing: dict[str, str] = {}
        self._embedding_routing: dict[str, str] = {}

    # ── 注册 ────────────────────────────────────────────

    def register_chat(
        self,
        name: str,
        provider_cls: type[ChatProvider],
        config_fn: Callable[[], ProviderConfig],
    ) -> None:
        """一次性注册聊天供应商的配置、策略类与模型路由。"""
        self.config_factory.register(name, config_fn)
        self.chat_factory.register(name, provider_cls)
        # 从类属性 SUPPORTED_MODELS 自动建立模型名 → 供应商名路由
        for model_name in getattr(provider_cls, "SUPPORTED_MODELS", []):
            self._chat_routing[model_name] = name

    def register_embedding(
        self,
        name: str,
        provider_cls: type[EmbeddingProvider],
        config_fn: Callable[[], ProviderConfig],
    ) -> None:
        """一次性注册嵌入供应商的配置、策略类与模型路由。"""
        self.config_factory.register(name, config_fn)
        self.embedding_factory.register(name, provider_cls)
        for model_name in getattr(provider_cls, "SUPPORTED_MODELS", []):
            self._embedding_routing[model_name] = name

    # ── 按供应商名称创建 ────────────────────────────────

    def create_chat_provider(
        self, name: str, config: Optional[ProviderConfig] = None
    ) -> ChatProvider:
        """按供应商名称创建聊天 Provider。"""
        if config is None:
            config = self.config_factory.create(name)
        return self.chat_factory.create(name, config)

    def create_embedding_provider(
        self, name: str, config: Optional[ProviderConfig] = None
    ) -> EmbeddingProvider:
        """按供应商名称创建嵌入 Provider。"""
        if config is None:
            config = self.config_factory.create(name)
        return self.embedding_factory.create(name, config)

    # ── 按模型名称路由 ─────────────────────────────────

    def get_chat_provider(self, model_name: str) -> ChatProvider:
        """根据模型名称路由到对应的聊天 Provider。"""
        provider_name = self._chat_routing.get(model_name)
        if provider_name is None:
            raise ModelNotSupportedException(model_name, list(self._chat_routing))
        return self.create_chat_provider(provider_name)

    def get_stream_client(self, model_name: str, *, temperature: float = 0.7, max_tokens: Optional[int] = None):
        """根据模型名称路由，获取带流式配置的 LangChain 客户端。"""
        provider = self.get_chat_provider(model_name)
        return provider.get_stream_client(model_name, temperature=temperature, max_tokens=max_tokens)

    def get_embedding_provider(self, model_name: str) -> EmbeddingProvider:
        """根据模型名称路由到对应的嵌入 Provider。"""
        provider_name = self._embedding_routing.get(model_name)
        if provider_name is None:
            raise ModelNotSupportedException(model_name, list(self._embedding_routing))
        return self.create_embedding_provider(provider_name)

    # ── 便捷方法 ────────────────────────────────────────

    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        """根据模型名称自动路由，发起聊天请求。"""
        provider = self.get_chat_provider(model_name)
        return provider.chat(request, model_name)

    def stream(self, request: ChatRequest, model_name: str):
        """根据模型名称自动路由，流式聊天，逐 token 返回。"""
        provider = self.get_chat_provider(model_name)
        return provider.stream(request, model_name)

    def embed(self, text: str, model_name: str) -> list[float]:
        """根据模型名称自动路由，获取文本嵌入向量。"""
        provider = self.get_embedding_provider(model_name)
        return provider.embed(text, model_name)

    def embed_batch(self, texts: list[str], model_name: str) -> list[list[float]]:
        """根据模型名称自动路由，批量获取嵌入向量。"""
        provider = self.get_embedding_provider(model_name)
        return provider.embed_batch(texts, model_name)

    def get_all_supported_chat_models(self) -> list[str]:
        """返回所有已注册聊天策略支持的模型名称列表。"""
        return list(self._chat_routing)

    def get_all_supported_embedding_models(self) -> list[str]:
        """返回所有已注册嵌入策略支持的模型名称列表。"""
        return list(self._embedding_routing)


# ======================================================================
# 装饰器 — 供应商自动注册（支持开闭原则）
# ======================================================================

def register_chat(name: str, config_fn: Callable[[], ProviderConfig]):
    """类装饰器：将聊天供应商自动注册到 llm_factory。

    用法::

        @register_chat("gemini", lambda: ProviderConfig(
            api_key=settings.get_key(settings.google_api_key),
        ))
        class GeminiProvider(ChatProvider):
            ...
    """
    def decorator(cls: type[ChatProvider]) -> type[ChatProvider]:
        llm_factory.register_chat(name, cls, config_fn)
        return cls
    return decorator


def register_embedding(name: str, config_fn: Callable[[], ProviderConfig]):
    """类装饰器：将嵌入供应商自动注册到 llm_factory。"""
    def decorator(cls: type[EmbeddingProvider]) -> type[EmbeddingProvider]:
        llm_factory.register_embedding(name, cls, config_fn)
        return cls
    return decorator


# ======================================================================
# 全局单例
# ======================================================================

llm_factory = LLMFactory()
