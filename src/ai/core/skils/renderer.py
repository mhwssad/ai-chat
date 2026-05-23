"""Skill prompt 渲染。"""

from __future__ import annotations

from jinja2 import Environment, StrictUndefined, TemplateError

from .errors import SkillRenderError


class SkillRenderer:
    """使用 Jinja2 渲染 Skill prompt。"""

    def __init__(self) -> None:
        self._env = Environment(
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
        )

    def render(self, prompt: str, variables: dict) -> str:
        try:
            return self._env.from_string(prompt).render(**variables)
        except TemplateError as exc:
            raise SkillRenderError("Skill 渲染失败", context={"error": str(exc)}) from exc

