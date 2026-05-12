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

    def create(self, name: str, model_name: Optional[str] = None, **kwargs):
        """创建 agent 实例。"""
        if name not in self._registry:
            raise KeyError(f"未注册的 agent: '{name}'，已注册: {list(self._registry)}")
        return self._registry[name](model_name=model_name, **kwargs)

    def list_agents(self) -> list[str]:
        return list(self._registry.keys())

    def get_label(self, name: str) -> str:
        return self._metadata.get(name, {}).get("label", name)

    def supports_overrides(self, name: str) -> bool:
        return self._metadata.get(name, {}).get("supports_overrides", False)

    def has_chat(self, name: str) -> bool:
        return self._metadata.get(name, {}).get("has_chat", False)


agent_factory = AgentFactory()
