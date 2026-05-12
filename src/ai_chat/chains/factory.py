"""Chain 工厂 — 注册和创建调用链实例。"""

from typing import Callable, Optional


class ChainFactory:
    """调用链工厂，按名称注册和创建 chain 实例。"""

    def __init__(self) -> None:
        self._registry: dict[str, type] = {}

    def register(self, name: str, cls: type) -> None:
        self._registry[name] = cls

    def create(self, name: str, model_name: Optional[str] = None, **kwargs):
        """创建 chain 实例。"""
        if name not in self._registry:
            raise KeyError(f"未注册的 chain: '{name}'，已注册: {list(self._registry)}")
        return self._registry[name](model_name=model_name, **kwargs)

    def list_chains(self) -> list[str]:
        return list(self._registry.keys())


chain_factory = ChainFactory()
