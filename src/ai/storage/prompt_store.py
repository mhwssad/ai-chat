"""DbPromptStore — 基于 PromptTemplateRepository 的 PromptStore 实现。"""

import logging

from src.ai.core.prompts.types import PromptData
from src.ai.storage.database import get_session
from src.ai.storage.prompt_repository import PromptTemplateRepository

logger = logging.getLogger(__name__)


class DbPromptStore:
    """提示词持久化实现，读写 prompt_templates 表。"""

    def get_by_key(
        self, prompt_key: str, *, enabled_only: bool = True
    ) -> PromptData | None:
        with get_session() as session:
            row = PromptTemplateRepository(session).get_by_key(
                prompt_key, enabled_only=enabled_only
            )
            if row is None:
                return None
            return _to_data(row)

    def save_template(
        self,
        *,
        prompt_key: str,
        template: str,
        display_name: str | None = None,
        description: str | None = None,
        category: str = "general",
        change_note: str | None = None,
    ) -> PromptData:
        with get_session() as session:
            row = PromptTemplateRepository(session).save_template(
                prompt_key=prompt_key,
                template=template,
                display_name=display_name,
                description=description,
                category=category,
                change_note=change_note,
            )
            return _to_data(row)

    def list_enabled(self, *, category: str | None = None) -> list[PromptData]:
        with get_session() as session:
            rows = PromptTemplateRepository(session).list_enabled(category=category)
            return [_to_data(row) for row in rows]


def _to_data(row) -> PromptData:
    """将 ORM PromptTemplate 映射为 PromptData。"""
    return PromptData(
        prompt_key=row.prompt_key,
        template=row.template,
        version=row.version,
        display_name=row.display_name,
        description=row.description,
        category=row.category,
        enabled=bool(row.enabled),
        extra=row.extra,
    )
