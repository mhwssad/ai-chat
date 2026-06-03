"""提示词服务 — CRUD 和渲染。"""

import json
import logging

from .ports import PromptStore
from .renderer import PromptRenderer
from .types import (
    PromptData,
    PromptRenderRequest,
    PromptRenderResult,
    PromptVersionData,
)

logger = logging.getLogger(__name__)


class PromptService:
    """提示词存储和渲染入口。

    职责：模板的增删改查和渲染。
    初始化种子数据由 seeder.py 负责，不在此处。
    """

    def __init__(
        self,
        renderer: PromptRenderer,
        store: PromptStore,
    ) -> None:
        self._renderer = renderer
        self._store = store

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
        """保存模板（新建或更新）。

        Args:
            prompt_key: 提示词键。
            template: 模板内容。
            display_name: 显示名称。
            description: 描述。
            category: 分类。
            change_note: 变更说明。

        Returns:
            保存后的 PromptData。
        """
        return self._store.save_template(
            prompt_key=prompt_key,
            template=template,
            display_name=display_name,
            description=description,
            category=category,
            change_note=change_note,
        )

    def get_template(self, prompt_key: str) -> PromptData | None:
        """按 key 获取模板。

        Args:
            prompt_key: 提示词键。

        Returns:
            模板数据，不存在则返回 None。
        """
        return self._store.get_by_key(prompt_key)

    def render(self, request: PromptRenderRequest) -> PromptRenderResult:
        """渲染提示词模板。

        Args:
            request: 渲染请求。

        Returns:
            渲染结果。

        Raises:
            PromptNotFoundError: 模板不存在。
        """
        prompt = self._store.get_by_key(request.prompt_key)
        if prompt is None:
            from src.ai.exception.prompt_exception import PromptNotFoundError

            raise PromptNotFoundError(
                "提示词不存在", context={"prompt_key": request.prompt_key}
            )
        content = self._renderer.render(prompt.template, request.variables)
        metadata = self._parse_extra(prompt.extra)
        return PromptRenderResult(
            prompt_key=prompt.prompt_key,
            content=content,
            version=prompt.version,
            metadata=metadata,
        )

    def list_templates(self, *, category: str | None = None) -> list[PromptData]:
        """列出已启用的模板。

        Args:
            category: 按分类过滤。

        Returns:
            模板列表。
        """
        return self._store.list_enabled(category=category)

    def delete_template(self, prompt_key: str, *, permanent: bool = False) -> bool:
        """删除模板。

        Args:
            prompt_key: 提示词键。
            permanent: 是否永久删除。

        Returns:
            是否成功删除。

        Raises:
            PromptNotFoundError: 模板不存在。
        """
        success = self._store.delete_template(prompt_key, permanent=permanent)
        if not success:
            from src.ai.exception.prompt_exception import PromptNotFoundError

            raise PromptNotFoundError(
                f"提示词不存在: {prompt_key}",
                context={"prompt_key": prompt_key},
            )
        return True

    def update_template(
        self,
        prompt_key: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
        category: str | None = None,
        enabled: bool | None = None,
    ) -> PromptData:
        """部分更新模板字段（不改模板内容，不产生新版本）。

        Args:
            prompt_key: 提示词键。
            display_name: 新显示名称。
            description: 新描述。
            category: 新分类。
            enabled: 启用状态。

        Returns:
            更新后的 PromptData。

        Raises:
            PromptNotFoundError: 模板不存在。
        """
        result = self._store.update_template(
            prompt_key,
            display_name=display_name,
            description=description,
            category=category,
            enabled=enabled,
        )
        if result is None:
            from src.ai.exception.prompt_exception import PromptNotFoundError

            raise PromptNotFoundError(
                f"提示词不存在: {prompt_key}",
                context={"prompt_key": prompt_key},
            )
        return result

    def list_versions(self, prompt_key: str) -> list[PromptVersionData]:
        """列出模板的版本历史。

        Args:
            prompt_key: 提示词键。

        Returns:
            版本历史列表。

        Raises:
            PromptNotFoundError: 模板不存在。
        """
        prompt = self._store.get_by_key(prompt_key, enabled_only=False)
        if prompt is None:
            from src.ai.exception.prompt_exception import PromptNotFoundError

            raise PromptNotFoundError(
                f"提示词不存在: {prompt_key}",
                context={"prompt_key": prompt_key},
            )
        return self._store.list_versions(prompt_key)

    def get_version(self, prompt_key: str, version: int) -> PromptVersionData:
        """获取模板的指定版本。

        Args:
            prompt_key: 提示词键。
            version: 版本号。

        Returns:
            版本数据。

        Raises:
            PromptNotFoundError: 模板或版本不存在。
        """
        result = self._store.get_version(prompt_key, version)
        if result is None:
            from src.ai.exception.prompt_exception import PromptNotFoundError

            raise PromptNotFoundError(
                f"版本不存在: {prompt_key} v{version}",
                context={"prompt_key": prompt_key, "version": version},
            )
        return result

    def rollback_template(
        self,
        prompt_key: str,
        version: int,
        *,
        change_note: str | None = None,
    ) -> PromptData:
        """回滚模板到指定版本（创建新版本，内容使用旧版本模板）。

        Args:
            prompt_key: 提示词键。
            version: 目标版本号。
            change_note: 回滚说明。

        Returns:
            回滚后的 PromptData。

        Raises:
            PromptNotFoundError: 模板或目标版本不存在。
        """
        result = self._store.rollback_template(
            prompt_key, version, change_note=change_note
        )
        if result is None:
            from src.ai.exception.prompt_exception import PromptNotFoundError

            raise PromptNotFoundError(
                f"回滚失败，模板或版本不存在: {prompt_key} v{version}",
                context={"prompt_key": prompt_key, "version": version},
            )
        return result

    def list_templates_paginated(
        self,
        *,
        category: str | None = None,
        enabled: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PromptData], int]:
        """分页列出模板。

        Args:
            category: 按分类过滤。
            enabled: 按启用状态过滤。
            page: 页码（从 1 开始）。
            page_size: 每页数量。

        Returns:
            (模板列表, 总数)。
        """
        offset = (page - 1) * page_size
        return self._store.list_all(
            category=category, enabled=enabled, limit=page_size, offset=offset
        )

    @staticmethod
    def _parse_extra(value: str | None) -> dict:
        """解析 extra JSON 字段。"""
        if not value:
            return {}
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}
