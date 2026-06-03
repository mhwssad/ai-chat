"""提示词数据库仓库。"""

from typing import Any

from sqlmodel import select

from src.ai.storage.base_repository import BaseRepository
from src.ai.storage.prompt_models import PromptTemplate, PromptVersion


class PromptTemplateRepository(BaseRepository[PromptTemplate]):
    """提示词模板仓库。"""

    model = PromptTemplate

    def get_by_key(
        self, prompt_key: str, *, enabled_only: bool = True
    ) -> PromptTemplate | None:
        """按键查找模板。

        Args:
            prompt_key: 提示词键。
            enabled_only: 是否只查找已启用的模板。

        Returns:
            模板实例，不存在则返回 None。
        """
        stmt = select(PromptTemplate).where(PromptTemplate.prompt_key == prompt_key)
        if enabled_only:
            stmt = stmt.where(PromptTemplate.enabled == True)  # noqa: E712
        return self.session.exec(stmt).first()

    def list_enabled(self, *, category: str | None = None) -> list[PromptTemplate]:
        """列出已启用的模板。

        Args:
            category: 按分类过滤。

        Returns:
            模板列表。
        """
        filters: dict[str, Any] = {"enabled": True}
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
        """保存模板（新建或更新），更新时自动归档旧版本。

        Args:
            prompt_key: 提示词键。
            template: 模板内容。
            display_name: 显示名称。
            description: 描述。
            category: 分类。
            change_note: 变更说明。

        Returns:
            保存后的模板实例。
        """
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
                display_name=display_name
                if display_name is not None
                else prompt.display_name,
                description=description
                if description is not None
                else prompt.description,
                category=category or prompt.category,
                version=prompt.version + 1,
            )
        return prompt

    def delete_template(self, prompt_key: str, *, permanent: bool = False) -> bool:
        """删除模板。

        Args:
            prompt_key: 提示词键。
            permanent: True 为硬删除，False 为软删除（禁用）。

        Returns:
            是否成功删除。
        """
        prompt = self.get_by_key(prompt_key, enabled_only=False)
        if prompt is None:
            return False
        if permanent:
            self.delete(prompt)
        else:
            self.update(prompt, enabled=False)
        return True

    def update_fields(
        self,
        prompt_key: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
        category: str | None = None,
        enabled: bool | None = None,
    ) -> PromptTemplate | None:
        """部分更新模板字段，不改 template 内容，不产生新版本。

        Args:
            prompt_key: 提示词键。
            display_name: 新显示名称（None 表示不修改）。
            description: 新描述（None 表示不修改）。
            category: 新分类（None 表示不修改）。
            enabled: 启用状态（None 表示不修改）。

        Returns:
            更新后的 PromptTemplate，不存在则返回 None。
        """
        prompt = self.get_by_key(prompt_key, enabled_only=False)
        if prompt is None:
            return None
        updates: dict[str, Any] = {}
        if display_name is not None:
            updates["display_name"] = display_name
        if description is not None:
            updates["description"] = description
        if category is not None:
            updates["category"] = category
        if enabled is not None:
            updates["enabled"] = enabled
        if updates:
            self.update(prompt, **updates)
        return prompt

    def list_all(
        self,
        *,
        category: str | None = None,
        enabled: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[PromptTemplate], int]:
        """列出所有模板（含禁用），支持分页。

        Args:
            category: 按分类过滤。
            enabled: 按启用状态过滤。
            limit: 每页数量。
            offset: 偏移量。

        Returns:
            (模板列表, 总数)。
        """
        filters: dict[str, Any] = {}
        if category is not None:
            filters["category"] = category
        if enabled is not None:
            filters["enabled"] = enabled
        total = self.count(**filters)
        items = self.list(
            limit=limit,
            offset=offset,
            order_by="prompt_key",
            descending=False,
            **filters,
        )
        return items, total


class PromptVersionRepository(BaseRepository[PromptVersion]):
    """提示词历史版本仓库。"""

    model = PromptVersion

    def list_by_prompt(self, prompt_id: int) -> list[PromptVersion]:
        """列出指定模板的版本历史。

        Args:
            prompt_id: 模板 ID。

        Returns:
            版本列表（按版本号降序）。
        """
        return self.list(prompt_id=prompt_id, order_by="version", descending=True)

    def get_by_prompt_and_version(
        self, prompt_id: int, version: int
    ) -> PromptVersion | None:
        """获取指定模板的指定版本。

        Args:
            prompt_id: 模板 ID。
            version: 版本号。

        Returns:
            版本记录，不存在则返回 None。
        """
        stmt = select(PromptVersion).where(
            PromptVersion.prompt_id == prompt_id,
            PromptVersion.version == version,
        )
        return self.session.exec(stmt).first()
