"""提示词服务。"""

from __future__ import annotations

import json

from src.ai.storage import PromptTemplate, PromptTemplateRepository, get_session

from .errors import PromptNotFoundError
from .renderer import PromptRenderer
from .types import PromptRenderRequest, PromptRenderResult


class PromptService:
    """提示词存储和渲染入口。"""

    def __init__(self, renderer: PromptRenderer | None = None) -> None:
        self._renderer = renderer or PromptRenderer()

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
        with get_session() as session:
            return PromptTemplateRepository(session).save_template(
                prompt_key=prompt_key,
                template=template,
                display_name=display_name,
                description=description,
                category=category,
                change_note=change_note,
            )

    def render(self, request: PromptRenderRequest) -> PromptRenderResult:
        with get_session() as session:
            prompt = PromptTemplateRepository(session).get_by_key(request.prompt_key)
            if prompt is None:
                raise PromptNotFoundError("提示词不存在", context={"prompt_key": request.prompt_key})
            content = self._renderer.render(prompt.template, request.variables)
            return PromptRenderResult(
                prompt_key=prompt.prompt_key,
                content=content,
                version=prompt.version,
                metadata=_loads_json(prompt.extra),
            )

    def list_templates(self, *, category: str | None = None) -> list[PromptTemplate]:
        with get_session() as session:
            return PromptTemplateRepository(session).list_enabled(category=category)


def _loads_json(value: str | None) -> dict:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


prompt_service = PromptService()

