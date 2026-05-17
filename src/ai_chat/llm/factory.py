"""抽象工厂 — 整合配置工厂、策略工厂与模型路由。"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import time
from dataclasses import fields as dataclass_fields
from typing import TYPE_CHECKING, Callable, Generic, Optional, TypeVar

from langchain_core.messages import HumanMessage

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.base import ModelProvider
from src.ai_chat.llm.models import (
    ChatRequest,
    ChatResponse,
    ModelNotSupportedException,
    ProviderConfig,
    mask_key,
)
from src.ai_chat.llm.observability import UsageEntry, error_logger, usage_tracker
from src.ai_chat.llm.resilience import wrap_with_resilience
from src.ai_chat.llm.token_utils import extract_prompt_tokens, extract_total_tokens
from src.ai_chat.utils.cache import LRUCache

if TYPE_CHECKING:
    from src.ai_chat.llm.providers.chat.base import ChatProvider
    from src.ai_chat.llm.providers.embedding.base import EmbeddingProvider

logger = get_logger(__name__)


# ======================================================================
# 配置工厂 — 按供应商名称创建 ProviderConfig
# ======================================================================


class ProviderConfigFactory:
    """通过供应商名称注册并创建 ProviderConfig。

    内部维护一个名称到工厂函数的映射表，支持运行时动态注册新供应商配置。
    """

    def __init__(self) -> None:
        self._registry: dict[str, Callable[[], ProviderConfig]] = {}

    def register(self, name: str, factory_fn: Callable[[], ProviderConfig]) -> None:
        """注册配置创建函数。

        Args:
            name: 供应商唯一标识名，如 'gemini'、'openai'
            factory_fn: 返回 ProviderConfig 实例的无参工厂函数
        """
        self._registry[name] = factory_fn
        logger.debug("已注册供应商配置: '%s'", name)

    def create(self, name: str, **overrides) -> ProviderConfig:
        """根据供应商名称创建 ProviderConfig，支持字段覆盖。

        Args:
            name: 已注册的供应商名称
            **overrides: 需要覆盖的配置字段（如 base_url、timeout）

        Raises:
            KeyError: 供应商名称未注册时抛出
        """
        if name not in self._registry:
            raise KeyError(
                f"未注册的供应商配置：'{name}'，已注册：{list(self._registry)}"
            )
        config = self._registry[name]()
        if overrides:
            valid = {f.name for f in dataclass_fields(config)}
            filtered = {k: v for k, v in overrides.items() if k in valid}
            config = dataclasses.replace(config, **filtered)
        logger.debug(
            "创建供应商配置 '%s'，base_url=%s, api_key=%s",
            name,
            config.base_url,
            mask_key(config.api_key),
        )
        return config


# ======================================================================
# 策略工厂 — 按供应商名称创建 Provider 实例
# ======================================================================

T = TypeVar("T")


class ProviderFactory(Generic[T]):
    """泛型策略工厂，按供应商名称创建 Provider 实例。

    利用 Python 泛型（Generic[T]）支持不同类型的 Provider（Chat、Embedding 等），
    每种类型维护独立的注册表。
    """

    def __init__(self) -> None:
        self._registry: dict[str, type[T]] = {}

    def register(self, name: str, cls: type[T]) -> None:
        """注册 Provider 类。

        Args:
            name: 供应商唯一标识名
            cls: Provider 类对象（非实例）
        """
        self._registry[name] = cls
        logger.debug("已注册 Provider 类: '%s' -> %s", name, cls.__name__)

    def create(self, name: str, config: Optional[ProviderConfig] = None) -> T:
        """创建 Provider 实例。

        Args:
            name: 已注册的供应商名称
            config: 可选的配置实例，传入后供 Provider 构造函数使用

        Raises:
            KeyError: 供应商名称未注册时抛出
        """
        if name not in self._registry:
            raise KeyError(f"未注册的供应商：'{name}'，已注册：{list(self._registry)}")
        instance = self._registry[name](config)
        logger.info("创建 Provider 实例: '%s' (%s)", name, type(instance).__name__)
        return instance

    @property
    def registered_names(self) -> list[str]:
        """返回所有已注册的供应商名称列表。"""
        return list(self._registry)


# ======================================================================
# 抽象工厂 — 泛型注册 + 模型路由
# ======================================================================


class LLMFactory:
    """抽象工厂，整合配置工厂、策略工厂与按模型名称路由。

    支持任意 provider_type（chat、embedding、image、video 等）的泛型注册。
    内部维护两个核心数据结构：
    - _provider_factories: provider_type -> ProviderFactory 映射
    - _routing: provider_type -> {model_name: provider_name} 模型路由表

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
        # 实例缓存: (provider_type, provider_name, config_hash) -> ModelProvider
        self._instance_cache: LRUCache[tuple[str, str, int], ModelProvider] = LRUCache(
            maxsize=64
        )
        # 响应缓存: (model_name, messages_hash, temperature, max_tokens) -> ChatResponse
        self._response_cache: LRUCache[
            tuple[str, str, float, Optional[int]], ChatResponse
        ] = LRUCache(maxsize=256, ttl=300.0)

    def _load_external_models(self) -> None:
        """从数据库加载外部模型到路由表。"""
        try:
            from src.ai_chat.llm.model_config import model_config_store

            chat_factory = self._provider_factories.get("chat")
            if not chat_factory:
                return
            registered_providers = set(chat_factory._registry)
            for mc in model_config_store.list_models(active_only=True):
                if mc.provider_name in registered_providers:
                    self._routing.setdefault("chat", {})[mc.model_name] = (
                        mc.provider_name
                    )
                    if mc.context_window:
                        from src.ai_chat.llm.model_metadata import (
                            MODEL_CONTEXT_SIZES,
                        )

                        MODEL_CONTEXT_SIZES[mc.model_name] = mc.context_window
            logger.debug("外部模型加载完成")
        except Exception as e:
            logger.warning("加载外部模型失败: %s", e)

    def refresh_models(self) -> None:
        """热重载模型配置（不清除实例缓存）。"""
        self._load_external_models()
        logger.info("模型配置已刷新")

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

        Args:
            provider_type: 提供商类别，如 'chat'、'embedding'
            name: 供应商唯一标识名
            provider_cls: Provider 类对象
            config_fn: 返回 ProviderConfig 的无参工厂函数
            requires_key: 是否要求 API 密钥存在才注册（本地模型如 Ollama 应设为 False）
        """
        if requires_key:
            config = config_fn()
            if config.api_key is None:
                logger.info("跳过注册 '%s' (%s): API 密钥未配置", name, provider_type)
                return

        # 按需创建该 provider_type 的工厂和路由表
        if provider_type not in self._provider_factories:
            self._provider_factories[provider_type] = ProviderFactory()
            self._routing[provider_type] = {}

        self.config_factory.register(name, config_fn)
        self._provider_factories[provider_type].register(name, provider_cls)

        # 遍历类上的 SUPPORTED_MODELS，建立 model_name -> provider_name 路由
        models = getattr(provider_cls, "SUPPORTED_MODELS", [])
        for model_name in models:
            self._routing[provider_type][model_name] = name

        logger.info(
            "已注册供应商 '%s' (类型=%s, 模型数量=%d, 模型列表=%s)",
            name,
            provider_type,
            len(models),
            models,
        )

        # 从 settings.llm_extra_models 扩展模型路由
        self._apply_extra_models(provider_type, name, provider_cls)

    def _get_provider(self, provider_type: str, model_name: str) -> ModelProvider:
        """按 provider_type 和 model_name 路由到对应的 Provider 实例。

        优先从实例缓存获取，缓存未命中时创建新实例并写入缓存。

        Args:
            provider_type: 提供商类别
            model_name: 目标模型名称

        Raises:
            ModelNotSupportedException: 模型名称未在路由表中时抛出
        """
        routing = self._routing.get(provider_type, {})
        provider_name = routing.get(model_name)
        if provider_name is None:
            logger.error(
                "[%s] 模型 '%s' 不在任何已注册供应商的支持列表中",
                provider_type,
                model_name,
            )
            raise ModelNotSupportedException(model_name, list(routing))

        logger.debug(
            "[%s] 路由模型 '%s' -> 供应商 '%s'",
            provider_type,
            model_name,
            provider_name,
        )
        config = self.config_factory.create(provider_name)

        cache_key = (provider_type, provider_name, self._config_hash(config))
        cached = self._instance_cache.get(cache_key)
        if cached is not None:
            logger.debug(
                "[%s] 命中实例缓存: provider='%s'", provider_type, provider_name
            )
            return cached

        instance = self._provider_factories[provider_type].create(provider_name, config)
        self._instance_cache.put(cache_key, instance)
        logger.debug("[%s] 创建并缓存实例: provider='%s'", provider_type, provider_name)
        return instance

    def _config_hash(self, config: ProviderConfig) -> int:
        """生成配置哈希值，用作实例缓存键。"""
        key_parts = (
            config.base_url or "",
            config.api_key.get_secret_value() if config.api_key else "",
            config.timeout,
        )
        return hash(key_parts)

    def _apply_extra_models(
        self, provider_type: str, provider_name: str, provider_cls: type
    ) -> None:
        """从 settings.llm_extra_models 解析并注册额外模型路由。"""
        from src.ai_chat.config import settings

        if not settings.llm_extra_models:
            return
        try:
            extra = json.loads(settings.llm_extra_models)
        except json.JSONDecodeError:
            logger.warning(
                "llm_extra_models JSON 格式无效: %s", settings.llm_extra_models
            )
            return

        models = extra.get(provider_name, [])
        if not models:
            return

        existing = set(getattr(provider_cls, "SUPPORTED_MODELS", []))
        new_models = [m for m in models if m not in existing]
        if new_models:
            provider_cls.SUPPORTED_MODELS = list(existing) + new_models
            for model_name in new_models:
                self._routing[provider_type][model_name] = provider_name
            logger.info(
                "从 llm_extra_models 扩展供应商 '%s' 模型: +%s",
                provider_name,
                new_models,
            )

    def _messages_hash(self, request: ChatRequest) -> str:
        """计算请求消息内容的哈希，用作响应缓存键。"""
        parts = []
        for msg in request.messages:
            content = msg.content if hasattr(msg, "content") else str(msg)
            if isinstance(content, list):
                content = json.dumps(content, ensure_ascii=False)
            msg_type = getattr(msg, "type", "unknown")
            parts.append(f"{msg_type}:{content}")
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]

    def clear_cache(self) -> None:
        """清空所有缓存（配置变更后调用）。"""
        self._instance_cache.clear()
        self._response_cache.clear()
        logger.info("已清空所有缓存（实例 + 响应）")

    def get_provider(self, provider_type: str, model_name: str) -> ModelProvider:
        """公开的泛型 provider 查询。

        Args:
            provider_type: 提供商类别
            model_name: 目标模型名称

        Returns:
            匹配的 ModelProvider 实例
        """
        return self._get_provider(provider_type, model_name)

    def get_supported_models(self, provider_type: str) -> list[str]:
        """返回指定类型下所有已注册模型名称列表。"""
        models = list(self._routing.get(provider_type, {}))
        logger.debug("[%s] 已注册模型: %s", provider_type, models)
        return models

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
        """按供应商名称创建聊天 Provider。

        Args:
            name: 供应商标识名
            config: 可选配置，None 时从配置工厂创建
        """
        if config is None:
            config = self.config_factory.create(name)
        logger.debug("创建聊天 Provider: '%s'", name)
        return self._provider_factories["chat"].create(name, config)

    def get_chat_provider(self, model_name: str) -> ChatProvider:
        """根据模型名称路由到对应的聊天 Provider。

        Args:
            model_name: 目标模型名称，如 'gpt-4o'、'gemini-2.0-flash'
        """
        provider = self._get_provider("chat", model_name)
        return provider  # type: ignore[return-value]

    def get_client(self, model_name: str):
        """获取聊天模型的 LangChain 客户端。

        封装 get_chat_provider().get_client()，一行获取客户端。

        Args:
            model_name: 目标模型名称

        Returns:
            配置好的 BaseChatModel 实例
        """
        provider = self.get_chat_provider(model_name)
        return provider.get_client(model_name)

    def bind_tools(self, model_name: str, tools: list):
        """获取绑定了工具的 LangChain 客户端。

        Args:
            model_name: 目标模型名称
            tools: LangChain BaseTool 列表

        Returns:
            绑定了工具的 BaseChatModel 实例
        """
        provider = self.get_chat_provider(model_name)
        return provider.get_client_with_tools(model_name, tools)

    def get_stream_client(
        self,
        model_name: str,
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ):
        """根据模型名称路由，获取带流式配置的 LangChain 客户端。

        Args:
            model_name: 目标模型名称
            temperature: 采样温度
            max_tokens: 最大生成 token 数
        """
        logger.debug(
            "获取流式客户端: model=%s, temperature=%.2f, max_tokens=%s",
            model_name,
            temperature,
            max_tokens,
        )
        provider = self.get_chat_provider(model_name)
        return provider.get_stream_client(
            model_name, temperature=temperature, max_tokens=max_tokens
        )

    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        """根据模型名称自动路由，发起聊天请求（带弹性策略、响应缓存和可观测）。"""
        logger.info(
            "发起聊天请求: model=%s, temperature=%.2f, max_tokens=%s, 消息数=%d",
            model_name,
            request.temperature,
            request.max_tokens,
            len(request.messages),
        )

        # 响应缓存检查
        cache_key = (
            model_name,
            self._messages_hash(request),
            request.temperature,
            request.max_tokens,
        )
        if not request.skip_cache:
            cached = self._response_cache.get(cache_key)
            if cached is not None:
                logger.debug("响应缓存命中: model=%s", model_name)
                return cached

        provider = self.get_chat_provider(model_name)
        provider_name = type(provider).__name__

        start = time.monotonic()
        try:
            response = wrap_with_resilience(
                provider_name,
                model_name,
                lambda: provider.chat(request, model_name),
                use_circuit_breaker=True,
            )
            duration_ms = (time.monotonic() - start) * 1000

            # 记录成功调用
            usage = response.usage or {}
            usage_tracker.record(
                UsageEntry(
                    provider=provider_name,
                    model=response.model,
                    input_tokens=extract_prompt_tokens(usage),
                    output_tokens=usage.get("output_tokens")
                    or usage.get("completion_tokens"),
                    total_tokens=extract_total_tokens(usage),
                    duration_ms=duration_ms,
                    success=True,
                )
            )

            # 写入响应缓存
            if response.content and not request.skip_cache:
                self._response_cache.put(cache_key, response)

            logger.info(
                "聊天响应完成: provider=%s, model=%s, 内容长度=%d, 耗时=%.0fms, usage=%s",
                provider_name,
                response.model,
                len(response.content),
                duration_ms,
                usage,
            )
            return response
        except Exception as e:
            duration_ms = (time.monotonic() - start) * 1000
            usage_tracker.record(
                UsageEntry(
                    provider=provider_name,
                    model=model_name,
                    duration_ms=duration_ms,
                    success=False,
                    error_type=type(e).__name__,
                )
            )
            error_logger.log_error(provider_name, model_name, e, duration_ms)
            raise

    def stream(
        self, request: ChatRequest, model_name: str, *, stop: Optional[list[str]] = None
    ):
        """根据模型名称自动路由，流式聊天（带重试和可观测）。"""
        logger.info("发起流式聊天请求: model=%s, stop=%s", model_name, stop)
        provider = self.get_chat_provider(model_name)
        provider_name = type(provider).__name__
        start = time.monotonic()

        def _tracked_generator():
            token_count = 0
            try:
                for chunk in wrap_with_resilience(
                    provider_name,
                    model_name,
                    lambda: provider.stream(request, model_name, stop=stop),
                    use_circuit_breaker=False,
                ):
                    token_count += 1
                    yield chunk
            except Exception as e:
                duration_ms = (time.monotonic() - start) * 1000
                usage_tracker.record(
                    UsageEntry(
                        provider=provider_name,
                        model=model_name,
                        duration_ms=duration_ms,
                        success=False,
                        error_type=type(e).__name__,
                    )
                )
                error_logger.log_error(provider_name, model_name, e, duration_ms)
                raise
            finally:
                duration_ms = (time.monotonic() - start) * 1000
                usage_tracker.record(
                    UsageEntry(
                        provider=provider_name,
                        model=model_name,
                        duration_ms=duration_ms,
                        success=True,
                    )
                )
                logger.info(
                    "流式聊天完成: provider=%s, model=%s, chunks=%d, 耗时=%.0fms",
                    provider_name,
                    model_name,
                    token_count,
                    duration_ms,
                )

        return _tracked_generator()

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
        self.register(
            "embedding", name, provider_cls, config_fn, requires_key=requires_key
        )

    def create_embedding_provider(
        self, name: str, config: Optional[ProviderConfig] = None
    ) -> EmbeddingProvider:
        """按供应商名称创建嵌入 Provider。

        Args:
            name: 供应商标识名
            config: 可选配置，None 时从配置工厂创建
        """
        if config is None:
            config = self.config_factory.create(name)
        logger.debug("创建嵌入 Provider: '%s'", name)
        return self._provider_factories["embedding"].create(name, config)

    def get_embedding_provider(self, model_name: str) -> EmbeddingProvider:
        """根据模型名称路由到对应的嵌入 Provider。"""
        provider = self._get_provider("embedding", model_name)
        return provider  # type: ignore[return-value]

    def embed(self, text: str, model_name: str) -> list[float]:
        """根据模型名称自动路由，获取文本嵌入向量（带弹性策略和可观测）。"""
        logger.info("计算嵌入向量: model=%s, 文本长度=%d", model_name, len(text))
        provider = self.get_embedding_provider(model_name)
        provider_name = type(provider).__name__

        start = time.monotonic()
        try:
            result = wrap_with_resilience(
                provider_name,
                model_name,
                lambda: provider.embed(text, model_name),
                use_circuit_breaker=True,
            )
            duration_ms = (time.monotonic() - start) * 1000
            usage_tracker.record(
                UsageEntry(
                    provider=provider_name,
                    model=model_name,
                    duration_ms=duration_ms,
                    success=True,
                )
            )
            logger.info(
                "嵌入向量完成: provider=%s, model=%s, 耗时=%.0fms",
                provider_name,
                model_name,
                duration_ms,
            )
            return result
        except Exception as e:
            duration_ms = (time.monotonic() - start) * 1000
            usage_tracker.record(
                UsageEntry(
                    provider=provider_name,
                    model=model_name,
                    duration_ms=duration_ms,
                    success=False,
                    error_type=type(e).__name__,
                )
            )
            error_logger.log_error(provider_name, model_name, e, duration_ms)
            raise

    def embed_batch(self, texts: list[str], model_name: str) -> list[list[float]]:
        """根据模型名称自动路由，批量获取嵌入向量（带弹性策略和可观测）。"""
        logger.info("批量计算嵌入向量: model=%s, 文本数量=%d", model_name, len(texts))
        provider = self.get_embedding_provider(model_name)
        provider_name = type(provider).__name__

        start = time.monotonic()
        try:
            result = wrap_with_resilience(
                provider_name,
                model_name,
                lambda: provider.embed_batch(texts, model_name),
                use_circuit_breaker=True,
            )
            duration_ms = (time.monotonic() - start) * 1000
            usage_tracker.record(
                UsageEntry(
                    provider=provider_name,
                    model=model_name,
                    duration_ms=duration_ms,
                    success=True,
                )
            )
            logger.info(
                "批量嵌入完成: provider=%s, model=%s, 数量=%d, 耗时=%.0fms",
                provider_name,
                model_name,
                len(texts),
                duration_ms,
            )
            return result
        except Exception as e:
            duration_ms = (time.monotonic() - start) * 1000
            usage_tracker.record(
                UsageEntry(
                    provider=provider_name,
                    model=model_name,
                    duration_ms=duration_ms,
                    success=False,
                    error_type=type(e).__name__,
                )
            )
            error_logger.log_error(provider_name, model_name, e, duration_ms)
            raise

    def get_all_supported_embedding_models(self) -> list[str]:
        """返回所有已注册嵌入策略支持的模型名称列表。"""
        return list(self._routing.get("embedding", {}))

    # ── 异步方法 ──────────────────────────────────────────

    async def achat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        """异步聊天请求（通过线程池运行同步弹性栈）。"""
        # 响应缓存检查
        cache_key = (
            model_name,
            self._messages_hash(request),
            request.temperature,
            request.max_tokens,
        )
        cached = self._response_cache.get(cache_key) if not request.skip_cache else None
        if cached is not None:
            logger.debug("异步响应缓存命中: model=%s", model_name)
            return cached

        provider = self.get_chat_provider(model_name)
        provider_name = type(provider).__name__

        def _sync_call():
            return wrap_with_resilience(
                provider_name,
                model_name,
                lambda: provider.chat(request, model_name),
                use_circuit_breaker=True,
            )

        start = time.monotonic()
        try:
            response = await asyncio.to_thread(_sync_call)
            duration_ms = (time.monotonic() - start) * 1000

            usage = response.usage or {}
            usage_tracker.record(
                UsageEntry(
                    provider=provider_name,
                    model=response.model,
                    input_tokens=extract_prompt_tokens(usage),
                    output_tokens=usage.get("output_tokens")
                    or usage.get("completion_tokens"),
                    total_tokens=extract_total_tokens(usage),
                    duration_ms=duration_ms,
                    success=True,
                )
            )
            if response.content and not request.skip_cache:
                self._response_cache.put(cache_key, response)

            logger.info(
                "异步聊天完成: provider=%s, model=%s, 耗时=%.0fms",
                provider_name,
                response.model,
                duration_ms,
            )
            return response
        except Exception as e:
            duration_ms = (time.monotonic() - start) * 1000
            usage_tracker.record(
                UsageEntry(
                    provider=provider_name,
                    model=model_name,
                    duration_ms=duration_ms,
                    success=False,
                    error_type=type(e).__name__,
                )
            )
            error_logger.log_error(provider_name, model_name, e, duration_ms)
            raise

    async def astream(
        self, request: ChatRequest, model_name: str, *, stop: Optional[list[str]] = None
    ):
        """异步流式聊天（通过线程池运行同步弹性栈）。"""
        provider = self.get_chat_provider(model_name)
        provider_name = type(provider).__name__
        start = time.monotonic()

        async for chunk in provider.astream(request, model_name, stop=stop):
            yield chunk

        duration_ms = (time.monotonic() - start) * 1000
        usage_tracker.record(
            UsageEntry(
                provider=provider_name,
                model=model_name,
                duration_ms=duration_ms,
                success=True,
            )
        )

    # ── 健康检查 ──────────────────────────────────────────

    def health_check(
        self,
        providers: list[str] | None = None,
        timeout: float = 10.0,
    ) -> dict[str, dict]:
        """探测聊天供应商的可用性。

        Args:
            providers: 指定检查的供应商列表，None 时检查全部
            timeout: 单个检查的超时时间（秒），用于日志标记

        Returns:
            {provider_name: {"available": bool, "latency_ms": float, "error": str | None}}
        """
        results = {}
        chat_factory = self._provider_factories.get("chat")
        if not chat_factory:
            return results

        targets = (
            {k: v for k, v in chat_factory._registry.items() if k in providers}
            if providers
            else chat_factory._registry
        )

        for provider_name, provider_cls in targets.items():
            supported = getattr(provider_cls, "SUPPORTED_MODELS", [])
            if not supported:
                results[provider_name] = {
                    "available": False,
                    "latency_ms": 0,
                    "error": "无支持模型",
                }
                continue

            test_model = supported[0]
            try:
                config = self.config_factory.create(provider_name)
                provider = chat_factory.create(provider_name, config)
                test_request = ChatRequest(
                    messages=[HumanMessage(content="hi")], max_tokens=1
                )
                start = time.monotonic()
                provider.chat(test_request, test_model)
                latency = (time.monotonic() - start) * 1000
                results[provider_name] = {
                    "available": True,
                    "latency_ms": round(latency, 0),
                    "error": None,
                }
            except Exception as e:
                results[provider_name] = {
                    "available": False,
                    "latency_ms": 0,
                    "error": str(e),
                }

        logger.info("健康检查完成: %s", {k: v["available"] for k, v in results.items()})
        return results


# ======================================================================
# 装饰器 — 供应商自动注册
# ======================================================================


def register(
    provider_type: str,
    name: str,
    config_fn: Callable[[], ProviderConfig],
    *,
    requires_key: bool = True,
):
    """泛型类装饰器：将供应商自动注册到 llm_factory。

    requires_key=False 时跳过密钥检查，始终注册（如 Ollama、本地模型）。

    Args:
        provider_type: 提供商类别
        name: 供应商唯一标识名
        config_fn: 配置工厂函数
        requires_key: 是否要求 API 密钥

    Returns:
        装饰器函数
    """

    def decorator(cls):
        logger.debug("装饰器触发注册: %s '%s' -> %s", provider_type, name, cls.__name__)
        llm_factory.register(
            provider_type, name, cls, config_fn, requires_key=requires_key
        )
        return cls

    return decorator


def register_chat(
    name: str, config_fn: Callable[[], ProviderConfig], *, requires_key: bool = True
):
    """类装饰器：将聊天供应商自动注册到 llm_factory。

    用法::

        @register_chat("gemini", lambda: ProviderConfig(
            api_key=settings.get_key(settings.google_api_key),
        ))
        class GeminiProvider(ChatProvider):
            ...
    """
    return register("chat", name, config_fn, requires_key=requires_key)


def register_embedding(
    name: str, config_fn: Callable[[], ProviderConfig], *, requires_key: bool = True
):
    """类装饰器：将嵌入供应商自动注册到 llm_factory。"""
    return register("embedding", name, config_fn, requires_key=requires_key)


# ======================================================================
# 全局单例
# ======================================================================

llm_factory = LLMFactory()
logger.info("LLMFactory 全局单例已创建")
