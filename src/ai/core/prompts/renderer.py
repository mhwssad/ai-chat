"""Jinja2 提示词渲染。"""


from jinja2 import Environment, StrictUndefined, TemplateError

from src.ai.exception.prompt_exception import PromptRenderError


class PromptRenderer:
    """渲染 Jinja2 提示词模板。"""

    def __init__(self) -> None:
        self._env = Environment(
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
        )

    def render(self, template: str, variables: dict) -> str:
        try:
            return self._env.from_string(template).render(**variables)
        except TemplateError as exc:
            raise PromptRenderError("提示词渲染失败", context={"error": str(exc)}) from exc

