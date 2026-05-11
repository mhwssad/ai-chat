"""Memory 抽象工厂 — 存储后端注册与创建。"""

from typing import Callable, Optional

from src.ai_chat.memory.models import (
    MemoryConfig,
    MemoryProvider,
    MemoryProviderNotFoundException,
)


class MemoryFactory:
    """存储后端工厂。"""

    def __init__(self) -> None:
        self._registry: dict[str, type[MemoryProvider]] = {}
        self._configs: dict[str, Callable[[], MemoryConfig]] = {}

    def register(
        self,
        name: str,
        provider_cls: type[MemoryProvider],
        config_fn: Callable[[], MemoryConfig],
    ) -> None:
        self._registry[name] = provider_cls
        self._configs[name] = config_fn

    def create(
        self,
        name: Optional[str] = None,
        config: Optional[MemoryConfig] = None,
    ) -> MemoryProvider:
        backend = name or "sqlite"
        if backend not in self._registry:
            raise MemoryProviderNotFoundException(backend, list(self._registry))
        if config is None:
            config = self._configs[backend]()
        return self._registry[backend](config)

    def list_providers(self) -> list[str]:
        return list(self._registry)


memory_factory = MemoryFactory()


def register_memory(name: str, config_fn: Callable[[], MemoryConfig]):
    """类装饰器：自动注册存储后端。"""

    def decorator(cls: type[MemoryProvider]) -> type[MemoryProvider]:
        memory_factory.register(name, cls, config_fn)
        return cls

    return decorator
