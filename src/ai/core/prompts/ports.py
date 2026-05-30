"""提示词持久化接口 — 依赖倒置，解耦 PromptService 与数据库。"""

from typing import Protocol, runtime_checkable

from .types import PromptData


@runtime_checkable
class PromptStore(Protocol):
    """提示词持久化接口。"""

    def get_by_key(
        self, prompt_key: str, *, enabled_only: bool = True
    ) -> PromptData | None: ...

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
