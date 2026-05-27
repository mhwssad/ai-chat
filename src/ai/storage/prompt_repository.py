"""提示词数据库仓库。"""


from sqlmodel import select

from src.ai.storage.base_repository import BaseRepository
from src.ai.storage.prompt_models import PromptTemplate, PromptVersion


class PromptTemplateRepository(BaseRepository[PromptTemplate]):
    """提示词模板仓库。"""

    model = PromptTemplate

    def get_by_key(self, prompt_key: str, *, enabled_only: bool = True) -> PromptTemplate | None:
        stmt = select(PromptTemplate).where(PromptTemplate.prompt_key == prompt_key)
        if enabled_only:
            stmt = stmt.where(PromptTemplate.enabled == True)  # noqa: E712
        return self.session.exec(stmt).first()

    def list_enabled(self, *, category: str | None = None) -> list[PromptTemplate]:
        filters = {"enabled": True}
        if category:
            filters["category"] = category
        return self.list(order_by="prompt_key", descending=False, **filters)

    def save_template(
        self,
        *,
        prompt_key: str,
        template: str,
        display_name: str | None = None,
        description: str | None = None,
        category: str = "general",
        change_note: str | None = None,
    ) -> PromptTemplate:
        prompt = self.get_by_key(prompt_key, enabled_only=False)
        if prompt is None:
            prompt = self.create(
                prompt_key=prompt_key,
                display_name=display_name,
                description=description,
                category=category,
                template=template,
                version=1,
            )
        else:
            PromptVersionRepository(self.session).create(
                prompt_id=prompt.id,
                version=prompt.version,
                template=prompt.template,
                change_note=change_note,
            )
            prompt = self.update(
                prompt,
                template=template,
                display_name=display_name if display_name is not None else prompt.display_name,
                description=description if description is not None else prompt.description,
                category=category or prompt.category,
                version=prompt.version + 1,
            )
        return prompt


class PromptVersionRepository(BaseRepository[PromptVersion]):
    """提示词历史版本仓库。"""

    model = PromptVersion

    def list_by_prompt(self, prompt_id: int) -> list[PromptVersion]:
        return self.list(prompt_id=prompt_id, order_by="version", descending=True)

