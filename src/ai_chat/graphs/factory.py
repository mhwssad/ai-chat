"""Agent 工厂 — 注册和创建 Agent 实例。"""

from typing import Optional


class AgentFactory:
    """Agent 工厂，按名称注册和创建 agent 实例。"""

    def __init__(self) -> None:
        self._registry: dict[str, type] = {}
        self._metadata: dict[str, dict] = {}

    def register(
        self,
        name: str,
        cls: type,
        *,
        supports_overrides: bool = False,
        has_chat: bool = False,
    ) -> None:
        self._registry[name] = cls
        self._metadata[name] = {
            "supports_overrides": supports_overrides,
            "has_chat": has_chat,
        }

    def unregister(self, name: str) -> None:
        """移除已注册的 agent。"""
        self._registry.pop(name, None)
        self._metadata.pop(name, None)

    def create(self, name: str, model_name: Optional[str] = None, **kwargs):
        """创建 agent 实例。"""
        if name not in self._registry:
            raise KeyError(f"未注册的 agent: '{name}'，已注册: {list(self._registry)}")
        return self._registry[name](model_name=model_name, **kwargs)

    def list_agents(self) -> list[str]:
        return list(self._registry.keys())

    def get_registry_info(self) -> list[dict[str, str | bool]]:
        """返回所有已注册 agent 的元信息。"""
        return [
            {
                "name": name,
                "class": cls.__name__,
                "supports_overrides": self._metadata.get(name, {}).get("supports_overrides", False),
                "has_chat": self._metadata.get(name, {}).get("has_chat", False),
            }
            for name, cls in self._registry.items()
        ]

    def get_label(self, name: str) -> str:
        return self._metadata.get(name, {}).get("label", name)

    def supports_overrides(self, name: str) -> bool:
        return self._metadata.get(name, {}).get("supports_overrides", False)

    def has_chat(self, name: str) -> bool:
        return self._metadata.get(name, {}).get("has_chat", False)

    def __contains__(self, name: str) -> bool:
        return name in self._registry

    def __len__(self) -> int:
        return len(self._registry)


def register_graph(name: str, *, supports_overrides: bool = False, has_chat: bool = False):
    """类装饰器：自动注册 agent 类到全局工厂。"""
    def decorator(cls: type) -> type:
        agent_factory.register(name, cls, supports_overrides=supports_overrides, has_chat=has_chat)
        return cls
    return decorator


agent_factory = AgentFactory()
