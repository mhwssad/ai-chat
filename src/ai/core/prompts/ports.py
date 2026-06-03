"""提示词持久化接口 — 依赖倒置，解耦 PromptService 与数据库。"""

from typing import Protocol, runtime_checkable

from .types import PromptData, PromptVersionData


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

    def delete_template(self, prompt_key: str, *, permanent: bool = False) -> bool:
        """删除模板。

        Args:
            prompt_key: 提示词键。
            permanent: True 为硬删除，False 为软删除（禁用）。

        Returns:
            是否成功删除。
        """
        ...

    def update_template(
        self,
        prompt_key: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
        category: str | None = None,
        enabled: bool | None = None,
    ) -> PromptData | None:
        """部分更新模板字段（不改模板内容，不产生新版本）。

        Args:
            prompt_key: 提示词键。
            display_name: 新显示名称。
            description: 新描述。
            category: 新分类。
            enabled: 启用状态。

        Returns:
            更新后的 PromptData，不存在则返回 None。
        """
        ...

    def list_versions(self, prompt_key: str) -> list[PromptVersionData]:
        """列出模板的版本历史。

        Args:
            prompt_key: 提示词键。

        Returns:
            版本历史列表（按版本号降序）。
        """
        ...

    def get_version(self, prompt_key: str, version: int) -> PromptVersionData | None:
        """获取模板的指定版本。

        Args:
            prompt_key: 提示词键。
            version: 版本号。

        Returns:
            版本数据，不存在则返回 None。
        """
        ...

    def rollback_template(
        self,
        prompt_key: str,
        version: int,
        *,
        change_note: str | None = None,
    ) -> PromptData | None:
        """回滚模板到指定版本（创建新版本，内容使用旧版本模板）。

        Args:
            prompt_key: 提示词键。
            version: 目标版本号。
            change_note: 回滚说明。

        Returns:
            回滚后的 PromptData，不存在则返回 None。
        """
        ...

    def list_all(
        self,
        *,
        category: str | None = None,
        enabled: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[PromptData], int]:
        """列出所有模板（含禁用），支持分页。

        Args:
            category: 按分类过滤。
            enabled: 按启用状态过滤。
            limit: 每页数量。
            offset: 偏移量。

        Returns:
            (模板列表, 总数)。
        """
        ...
