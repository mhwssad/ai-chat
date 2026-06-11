"""提示词 API 服务 — PromptService 的薄包装。

共享服务层，CLI 和 API 路由统一使用。
"""

from __future__ import annotations

from dataclasses import asdict
from src.ai.config.logging_setup import get_logger
from typing import Any

logger = get_logger(__name__)


class PromptApiService:
    """提示词 API 服务。

    职责：
    1. 模板 CRUD（创建、读取、更新、删除）
    2. 模板渲染
    3. 版本管理（列表、获取、回滚）
    """

    def __init__(self, *, prompt_service: Any) -> None:
        self._svc = prompt_service

    # ── CRUD ──────────────────────────────────────────────────

    def save_template(
        self,
        *,
        prompt_key: str,
        template: str,
        display_name: str | None = None,
        description: str | None = None,
        category: str = "general",
        change_note: str | None = None,
    ) -> dict[str, Any]:
        """保存提示词模板。

        Args:
            prompt_key: 模板唯一键。
            template: Jinja2 模板内容。
            display_name: 显示名称。
            description: 描述。
            category: 分类。
            change_note: 变更说明。

        Returns:
            模板数据字典。
        """
        data = self._svc.save_template(
            prompt_key=prompt_key,
            template=template,
            display_name=display_name,
            description=description,
            category=category,
            change_note=change_note,
        )
        return asdict(data)

    def get_template(self, prompt_key: str) -> dict[str, Any]:
        """获取提示词模板。

        Args:
            prompt_key: 模板键。

        Returns:
            模板数据字典。
        """
        data = self._svc.get_template(prompt_key)
        return asdict(data)

    def list_templates(
        self,
        *,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """列出提示词模板。

        Args:
            category: 按分类过滤。

        Returns:
            模板列表。
        """
        templates = self._svc.list_templates(category=category)
        return [asdict(t) for t in templates]

    def update_template(
        self,
        prompt_key: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
        category: str | None = None,
        enabled: bool | None = None,
    ) -> dict[str, Any]:
        """更新提示词模板元数据。

        Args:
            prompt_key: 模板键。
            display_name: 显示名称。
            description: 描述。
            category: 分类。
            enabled: 是否启用。

        Returns:
            更新后的模板数据字典。
        """
        data = self._svc.update_template(
            prompt_key,
            display_name=display_name,
            description=description,
            category=category,
            enabled=enabled,
        )
        return asdict(data)

    def delete_template(self, prompt_key: str) -> None:
        """删除提示词模板。

        Args:
            prompt_key: 模板键。
        """
        self._svc.delete_template(prompt_key)

    # ── 渲染 ──────────────────────────────────────────────────

    def render(
        self,
        *,
        prompt_key: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """渲染提示词模板。

        Args:
            prompt_key: 模板键。
            variables: 模板变量。

        Returns:
            渲染结果字典。
        """
        result = self._svc.render(prompt_key=prompt_key, variables=variables)
        return asdict(result)

    # ── 版本管理 ──────────────────────────────────────────────

    def list_versions(self, prompt_key: str) -> list[dict[str, Any]]:
        """列出模板的版本历史。

        Args:
            prompt_key: 模板键。

        Returns:
            版本列表。
        """
        versions = self._svc.list_versions(prompt_key)
        return [asdict(v) for v in versions]

    def get_version(self, prompt_key: str, version: int) -> dict[str, Any]:
        """获取指定版本。

        Args:
            prompt_key: 模板键。
            version: 版本号。

        Returns:
            版本数据字典。
        """
        data = self._svc.get_version(prompt_key, version)
        return asdict(data)

    def rollback_template(
        self,
        prompt_key: str,
        *,
        version: int,
        change_note: str | None = None,
    ) -> dict[str, Any]:
        """回滚模板到指定版本。

        Args:
            prompt_key: 模板键。
            version: 目标版本号。
            change_note: 回滚说明。

        Returns:
            回滚后的模板数据字典。
        """
        data = self._svc.rollback_template(
            prompt_key, version=version, change_note=change_note
        )
        return asdict(data)
