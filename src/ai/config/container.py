"""统一配置容器 — 管理所有配置项的依赖注入、生命周期和热更新。

替换分散在 AppContainer 中的配置 Provider，提供统一入口：
- 注册：container.register("name", FactoryClass, lifecycle=SINGLETON)
- 获取：container.get("name") 或 container.name
- 刷新：container.refresh("name") 或 container.refresh() 全量刷新
"""

from __future__ import annotations

import threading
from enum import Enum, auto
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")


# -- 生命周期 --


class Lifecycle(Enum):
    """配置对象的生命周期策略。"""

    SINGLETON = auto()
    """应用全局唯一，首次获取时创建，后续复用。"""

    TRANSIENT = auto()
    """每次获取都新建实例，适合需要频繁重载的配置。"""

    SCOPED = auto()
    """作用域内唯一，同一 scope 复用，跨 scope 隔离。"""


# -- Provider --


class ConfigProvider(Generic[T]):
    """配置项提供器 — 封装工厂函数、生命周期和缓存。

    Args:
        factory: 无参构造回调，延迟创建配置实例。
        lifecycle: 生命周期策略。
    """

    __slots__ = ("_factory", "_lifecycle", "_singleton", "_scoped", "_lock")

    def __init__(
        self,
        factory: Callable[[], T],
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
    ) -> None:
        self._factory = factory
        self._lifecycle = lifecycle
        self._singleton: T | None = None
        self._scoped: dict[str, T] = {}
        self._lock = threading.Lock()

    # -- 属性 --

    @property
    def lifecycle(self) -> Lifecycle:
        return self._lifecycle

    @property
    def is_created(self) -> bool:
        """检查 SINGLETON 是否已创建。"""
        return self._singleton is not None

    # -- 核心方法 --

    def get(self, scope: str = "__default__") -> T:
        """获取配置实例，根据生命周期决定复用或新建。

        Args:
            scope: 作用域标识，仅 SCOPED 生命周期使用。

        Returns:
            配置实例。
        """
        if self._lifecycle is Lifecycle.SINGLETON:
            if self._singleton is None:
                with self._lock:
                    if self._singleton is None:
                        self._singleton = self._factory()
            return self._singleton

        if self._lifecycle is Lifecycle.SCOPED:
            if scope not in self._scoped:
                with self._lock:
                    if scope not in self._scoped:
                        self._scoped[scope] = self._factory()
            return self._scoped[scope]

        # TRANSIENT
        return self._factory()

    def refresh(self) -> None:
        """强制失效缓存，下次获取将重新调用工厂创建实例。"""
        with self._lock:
            self._singleton = None
            self._scoped.clear()

    def replace(self, instance: T) -> None:
        """直接替换缓存的 SINGLETON 实例（用于测试 Mock）。

        Args:
            instance: 替换用的实例。
        """
        with self._lock:
            self._singleton = instance


# -- 容器 --


class ConfigContainer:
    """统一配置依赖注入容器。

    管理所有配置项的注册、获取、刷新。
    通过 ``container.name`` 或 ``container.get("name")`` 获取配置实例。

    生命周期策略：
    - SINGLETON：全局业务配置（Settings, BootstrapSettings）
    - SINGLETON + refresh 支持：模型配置（ChatModelConfig 等），支持热切换
    - TRANSIENT：需要每次读取最新环境变量的场景

    Example:
        >>> container = ConfigContainer()
        >>> settings = container.settings
        >>> chat_cfg = container.get("chat_model_config")
        >>> container.refresh()  # 全量热更新
    """

    def __init__(self, *, watch_env: bool = False) -> None:
        self._providers: dict[str, ConfigProvider[Any]] = {}
        self._watcher: threading.Thread | None = None
        self._register_defaults()

        if watch_env:
            self._start_watcher()

    # -- 注册 --

    def register(
        self,
        name: str,
        factory: Callable[[], Any] | type,
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
    ) -> ConfigProvider:
        """注册一个配置项。

        Args:
            name: 唯一标识，同时作为属性名。
            factory: 工厂函数或无参构造类。传入类时自动包装为 ``lambda: cls()``。
            lifecycle: 生命周期策略。

        Returns:
            创建的 ConfigProvider，可用于后续 replace 等操作。

        Raises:
            ValueError: name 已存在。
        """
        if name in self._providers:
            raise ValueError(f"Config provider '{name}' already registered")

        if isinstance(factory, type):
            _cls = factory
            factory = lambda: _cls()  # noqa: E731

        provider = ConfigProvider[Any](factory, lifecycle)
        self._providers[name] = provider
        return provider

    def unregister(self, name: str) -> None:
        """移除配置项注册。

        Args:
            name: 配置项名称。
        """
        self._providers.pop(name, None)

    # -- 获取 --

    def get(self, name: str, scope: str = "__default__") -> Any:
        """通过名称获取配置实例。

        Args:
            name: 配置项名称。
            scope: 作用域标识，仅 SCOPED 生命周期使用。

        Returns:
            配置实例。

        Raises:
            KeyError: name 未注册。
        """
        provider = self._providers.get(name)
        if provider is None:
            raise KeyError(f"Config '{name}' is not registered")
        return provider.get(scope)

    def provider(self, name: str) -> ConfigProvider:
        """获取注册的 ConfigProvider 对象（用于 replace 等高级操作）。

        Args:
            name: 配置项名称。

        Returns:
            ConfigProvider 实例。

        Raises:
            KeyError: name 未注册。
        """
        provider = self._providers.get(name)
        if provider is None:
            raise KeyError(f"Config '{name}' is not registered")
        return provider

    # -- 刷新 --

    def refresh(self, name: str | None = None) -> None:
        """刷新配置缓存。

        Args:
            name: 指定名称，None 表示全量刷新所有已注册的配置。
        """
        if name is not None:
            provider = self._providers.get(name)
            if provider is not None:
                provider.refresh()
            return

        for provider in self._providers.values():
            provider.refresh()

    # -- 属性访问 --

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self._providers:
            return self._providers[name].get()
        raise AttributeError(f"'{type(self).__name__}' has no config '{name}'")

    def __dir__(self) -> list[str]:
        return list(self._providers.keys())

    # -- 内部: 注册默认配置 --

    def _register_defaults(self) -> None:
        """注册所有内置配置项。"""
        from src.ai.config.base_config import BootstrapSettings
        from src.ai.config.loader_settings import LoaderSettings
        from src.ai.config.logging_setup import LogConfig
        from src.ai.config.model_settings import (
            ChatModelConfig,
            EmbeddingModelConfig,
            ImageModelConfig,
            TTSModelConfig,
        )
        from src.ai.config.settings import Settings

        # 基础设施配置 — SINGLETON，启动期创建
        self.register("bootstrap_settings", BootstrapSettings)
        self.register("settings", Settings)

        # 模型连接配置 — SINGLETON，支持热刷新
        self.register("chat_model_config", ChatModelConfig)
        self.register("embedding_model_config", EmbeddingModelConfig)
        self.register("image_model_config", ImageModelConfig)
        self.register("tts_model_config", TTSModelConfig)

        # 加载器配置 — SINGLETON
        self.register("loader_settings", LoaderSettings)

        # 日志配置 — SINGLETON
        self.register("log_config", LogConfig)

    # -- 内部: 文件监控热更新 --

    def _start_watcher(self) -> None:
        """启动 .env 文件变更监控线程。"""
        import time
        from pathlib import Path

        from src.ai.config.base_config import env_file_path

        env_file = env_file_path
        if not env_file or not Path(env_file).exists():
            return

        env_path = Path(env_file)
        last_mtime = env_path.stat().st_mtime

        def _watch() -> None:
            nonlocal last_mtime
            while True:
                time.sleep(2)
                try:
                    current = env_path.stat().st_mtime
                    if current != last_mtime:
                        last_mtime = current
                        self.refresh()
                        import logging

                        logging.getLogger(__name__).info(
                            "检测到 .env 变更，配置已自动刷新"
                        )
                except Exception:
                    pass

        self._watcher = threading.Thread(target=_watch, daemon=True, name="config-watcher")
        self._watcher.start()


# -- 模块级实例 --

config = ConfigContainer()
"""模块级配置容器实例，应用全局唯一。"""
