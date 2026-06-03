"""DbPromptStore — 基于 PromptTemplateRepository 的 PromptStore 实现。"""

import logging

from src.ai.core.prompts.types import PromptData, PromptVersionData
from src.ai.storage.database import get_session
from src.ai.storage.prompt_repository import (
    PromptTemplateRepository,
    PromptVersionRepository,
)

logger = logging.getLogger(__name__)


class DbPromptStore:
    """提示词持久化实现，读写 prompt_templates 表。"""

    def get_by_key(
        self, prompt_key: str, *, enabled_only: bool = True
    ) -> PromptData | None:
        """按键查找模板。"""
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
        """保存模板（新建或更新）。"""
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
        """列出已启用的模板。"""
        with get_session() as session:
            rows = PromptTemplateRepository(session).list_enabled(category=category)
            return [_to_data(row) for row in rows]

    def delete_template(self, prompt_key: str, *, permanent: bool = False) -> bool:
        """删除模板。"""
        with get_session() as session:
            return PromptTemplateRepository(session).delete_template(
                prompt_key, permanent=permanent
            )

    def update_template(
        self,
        prompt_key: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
        category: str | None = None,
        enabled: bool | None = None,
    ) -> PromptData | None:
        """部分更新模板字段。"""
        with get_session() as session:
            row = PromptTemplateRepository(session).update_fields(
                prompt_key,
                display_name=display_name,
                description=description,
                category=category,
                enabled=enabled,
            )
            if row is None:
                return None
            return _to_data(row)

    def list_versions(self, prompt_key: str) -> list[PromptVersionData]:
        """列出模板的版本历史。"""
        with get_session() as session:
            prompt = PromptTemplateRepository(session).get_by_key(
                prompt_key, enabled_only=False
            )
            if prompt is None:
                return []
            versions = PromptVersionRepository(session).list_by_prompt(prompt.id)
            return [_version_to_data(v) for v in versions]

    def get_version(self, prompt_key: str, version: int) -> PromptVersionData | None:
        """获取指定版本。"""
        with get_session() as session:
            prompt = PromptTemplateRepository(session).get_by_key(
                prompt_key, enabled_only=False
            )
            if prompt is None:
                return None
            v = PromptVersionRepository(session).get_by_prompt_and_version(
                prompt.id, version
            )
            if v is None:
                return None
            return _version_to_data(v)

    def rollback_template(
        self,
        prompt_key: str,
        version: int,
        *,
        change_note: str | None = None,
    ) -> PromptData | None:
        """回滚模板到指定版本。"""
        with get_session() as session:
            prompt = PromptTemplateRepository(session).get_by_key(
                prompt_key, enabled_only=False
            )
            if prompt is None:
                return None
            v = PromptVersionRepository(session).get_by_prompt_and_version(
                prompt.id, version
            )
            if v is None:
                return None
            note = change_note or f"回滚到版本 {version}"
            updated = PromptTemplateRepository(session).save_template(
                prompt_key=prompt_key,
                template=v.template,
                display_name=prompt.display_name,
                description=prompt.description,
                category=prompt.category,
                change_note=note,
            )
            return _to_data(updated)

    def list_all(
        self,
        *,
        category: str | None = None,
        enabled: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[PromptData], int]:
        """列出所有模板（含禁用），支持分页。"""
        with get_session() as session:
            items, total = PromptTemplateRepository(session).list_all(
                category=category, enabled=enabled, limit=limit, offset=offset
            )
            return [_to_data(row) for row in items], total


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


def _version_to_data(row) -> PromptVersionData:
    """将 ORM PromptVersion 映射为 PromptVersionData。"""
    return PromptVersionData(
        id=row.id,
        prompt_id=row.prompt_id,
        version=row.version,
        template=row.template,
        change_note=row.change_note,
    )
