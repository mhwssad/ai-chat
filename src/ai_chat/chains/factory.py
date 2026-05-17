"""Chain 工厂 — 注册和创建调用链实例。"""

from typing import Optional


class ChainFactory:
    """调用链工厂，按名称注册和创建 chain 实例。"""

    def __init__(self) -> None:
        self._registry: dict[str, type] = {}

    def register(self, name: str, cls: type) -> None:
        """注册 chain 类。"""
        self._registry[name] = cls

    def unregister(self, name: str) -> None:
        """移除已注册的 chain 类。"""
        self._registry.pop(name, None)

    def create(self, name: str, model_name: Optional[str] = None, **kwargs):
        """创建 chain 实例。"""
        if name not in self._registry:
            raise KeyError(f"未注册的 chain: '{name}'，已注册: {list(self._registry)}")
        return self._registry[name](model_name=model_name, **kwargs)

    def create_many(
        self,
        names: list[str],
        model_name: Optional[str] = None,
        **kwargs,
    ) -> dict[str, object]:
        """批量创建 chain 实例，返回 {name: instance}。"""
        return {name: self.create(name, model_name=model_name, **kwargs) for name in names}

    def list_chains(self) -> list[str]:
        return list(self._registry.keys())

    def get_registry_info(self) -> list[dict[str, str]]:
        """返回所有已注册 chain 类型的元信息。"""
        return [{"name": name, "class": cls.__name__} for name, cls in self._registry.items()]

    def __contains__(self, name: str) -> bool:
        return name in self._registry

    def __len__(self) -> int:
        return len(self._registry)


def register_chain(name: str):
    """类装饰器：自动注册 chain 类到全局工厂。

    用法::

        @register_chain("chat")
        class ChatChain(_BasePromptChain): ...
    """
    def decorator(cls: type) -> type:
        chain_factory.register(name, cls)
        return cls
    return decorator


chain_factory = ChainFactory()
