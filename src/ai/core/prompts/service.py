"""提示词服务 — CRUD 和渲染。"""

import json
import logging

from .ports import PromptStore
from .renderer import PromptRenderer
from .types import PromptData, PromptRenderRequest, PromptRenderResult

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
        """保存模板（新建或更新）。"""
        return self._store.save_template(
            prompt_key=prompt_key,
            template=template,
            display_name=display_name,
            description=description,
            category=category,
            change_note=change_note,
        )

    def get_template(self, prompt_key: str) -> PromptData | None:
        """按 key 获取模板。"""
        return self._store.get_by_key(prompt_key)

    def render(self, request: PromptRenderRequest) -> PromptRenderResult:
        """渲染提示词模板。"""
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
        """列出已启用的模板。"""
        return self._store.list_enabled(category=category)

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
