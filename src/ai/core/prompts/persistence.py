"""提示词持久化 Protocol — 解耦 PromptService 与数据库。"""


from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class PromptData:
    """提示词模板数据，替代直接依赖 ORM PromptTemplate。"""

    prompt_key: str
    template: str
    version: int = 1
    display_name: str | None = None
    description: str | None = None
    category: str = "general"
    enabled: bool = True
    extra: str = "{}"


@runtime_checkable
class PromptStore(Protocol):
    """提示词持久化接口。"""

    def get_by_key(self, prompt_key: str, *, enabled_only: bool = True) -> PromptData | None: ...

    def save_template(
        self,
        *,
        prompt_key: str,
        template: str,
        display_name: str | None = None,
        description: str | None = None,
        category: str = "general",
        change_note: str | None = None,
    ) -> PromptData: ...

    def list_enabled(self, *, category: str | None = None) -> list[PromptData]: ...
