"""Memory 抽象工厂 — 存储后端注册与创建。

提供 MemoryFactory 单例和 @register_memory 类装饰器，
支持运行时动态注册新的存储后端（如 Redis、Postgres 等）。
"""

from typing import Callable, Optional

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.memory.models import (
    MemoryConfig,
    MemoryProvider,
    MemoryProviderNotFoundException,
)

logger = get_logger(__name__)


class MemoryFactory:
    """存储后端工厂，按名称注册并创建 MemoryProvider 实例。

    内部维护两个映射表:
    - _registry: 后端名称 -> Provider 类
    - _configs: 后端名称 -> 默认配置工厂函数
    """

    def __init__(self) -> None:
        self._registry: dict[str, type[MemoryProvider]] = {}
        self._configs: dict[str, Callable[[], MemoryConfig]] = {}

    def register(
        self,
        name: str,
        provider_cls: type[MemoryProvider],
        config_fn: Callable[[], MemoryConfig],
    ) -> None:
        """注册存储后端。

        Args:
            name: 后端唯一标识名，如 'sqlite'、'in_memory'
            provider_cls: MemoryProvider 子类
            config_fn: 返回默认 MemoryConfig 的无参工厂函数
        """
        self._registry[name] = provider_cls
        self._configs[name] = config_fn
        logger.debug("已注册存储后端: '%s' -> %s", name, provider_cls.__name__)

    def create(
        self,
        name: Optional[str] = None,
        config: Optional[MemoryConfig] = None,
    ) -> MemoryProvider:
        """创建存储后端实例。

        Args:
            name: 后端名称，None 时默认使用 'sqlite'
            config: 可选的配置实例，None 时使用注册时的默认配置

        Raises:
            MemoryProviderNotFoundException: 后端名称未注册时抛出
        """
        backend = name or "sqlite"
        if backend not in self._registry:
            raise MemoryProviderNotFoundException(backend, list(self._registry))
        if config is None:
            config = self._configs[backend]()
        instance = self._registry[backend](config)  # type: ignore[call-arg]
        logger.debug("创建存储后端实例: '%s' (%s)", backend, type(instance).__name__)
        return instance

    def list_providers(self) -> list[str]:
        """返回所有已注册的后端名称列表。"""
        return list(self._registry)


# 全局单例，供 @register_memory 装饰器和调用方使用
memory_factory = MemoryFactory()


def register_memory(name: str, config_fn: Callable[[], MemoryConfig]):
    """类装饰器：将 MemoryProvider 子类自动注册到全局 memory_factory。

    用法::

        @register_memory("sqlite", lambda: MemoryConfig())
        class SQLiteStore(MemoryProvider):
            ...

    Args:
        name: 后端唯一标识名
        config_fn: 返回默认 MemoryConfig 的无参工厂函数

    Returns:
        装饰器函数（不修改原始类）
    """

    def decorator(cls: type[MemoryProvider]) -> type[MemoryProvider]:
        logger.debug("装饰器触发注册: 存储后端 '%s' -> %s", name, cls.__name__)
        memory_factory.register(name, cls, config_fn)
        return cls

    return decorator
