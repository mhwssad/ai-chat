"""提示词服务。"""


import json
import logging

from .persistence import PromptData, PromptStore
from .renderer import PromptRenderer
from .types import PromptRenderRequest, PromptRenderResult

logger = logging.getLogger(__name__)

# 预置默认模板：prompt_key → (display_name, description, category, template)
_DEFAULT_TEMPLATES: dict[str, tuple[str, str, str, str]] = {
    "memory.system_prompt": (
        "记忆系统提示词",
        "注入模型的记忆系统说明，包含记忆类型、使用规则和 MEMORY.md 入口",
        "memory",
        (
            "# {{ display_name }} Memory\n"
            "\n"
            "记忆类型：\n"
            "- user：用户角色、目标、职责、偏好和稳定知识。\n"
            "- feedback：用户给出的工作指导、纠正和确认。\n"
            "- project：当前项目目标、正在进行的工作、bug 和事件。\n"
            "- reference：外部系统资源指针，例如 issue、文档或任务链接。\n"
            "\n"
            "使用规则：\n"
            "- 只使用和当前任务相关的记忆。\n"
            "- 不保存可从代码直接推导出的普通实现细节。\n"
            "- 不保存 API Key、token、密码或其他敏感信息。\n"
            "- 当记忆和当前用户指令冲突时，以当前用户指令为准。"
            "{% if extra_guidelines %}\n"
            "\n"
            "额外规则：\n"
            "{% for item in extra_guidelines -%}\n"
            "- {{ item }}\n"
            "{% endfor %}{% endif %}"
            "{% if entrypoint %}\n"
            "\n"
            "## MEMORY.md\n"
            "{{ entrypoint }}{% endif %}"
        ),
    ),
    "memory.context_header": (
        "上下文记忆头部",
        "将上下文记忆条目格式化为可注入模型的提示片段",
        "memory",
        (
            "# {{ display_name }} Memory\n"
            "{% for entry in entries -%}\n"
            "{{ entry.label }} {{ entry.content }}\n"
            "{% endfor %}"
        ),
    ),
    "memory.context_section": (
        "上下文记忆片段",
        "将记忆条目格式化为 markdown 子章节",
        "memory",
        (
            "## {{ section_title }}\n"
            "{% for entry in entries -%}\n"
            "- {{ entry.content }}\n"
            "{% endfor %}"
        ),
    ),
    "rag.context_format": (
        "RAG 上下文格式",
        "将 RAG 检索结果格式化为可注入模型的上下文文本",
        "rag",
        (
            "{% for result in results %}{% if not loop.first %}\n"
            "\n"
            "{% endif %}[{{ result.index }}] {{ result.title }}\n"
            "{{ result.content }}{% endfor %}"
        ),
    ),
    "chat.system_prompt": (
        "聊天系统提示词",
        "注入模型的默认系统提示词，可由调用方覆盖",
        "chat",
        "你是一个有帮助的 AI 助手。",
    ),
}


class PromptService:
    """提示词存储和渲染入口。"""

    def __init__(
        self,
        renderer: PromptRenderer | None = None,
        store: PromptStore | None = None,
    ) -> None:
        self._renderer = renderer or PromptRenderer()
        self._store = store

    def _get_store(self) -> PromptStore:
        """获取 store 实例，延迟创建默认实现。"""
        if self._store is None:
            from src.ai.storage.prompt_store import DbPromptStore
            self._store = DbPromptStore()
        return self._store

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
        return self._get_store().save_template(
            prompt_key=prompt_key,
            template=template,
            display_name=display_name,
            description=description,
            category=category,
            change_note=change_note,
        )

    def render(self, request: PromptRenderRequest) -> PromptRenderResult:
        prompt = self._get_store().get_by_key(request.prompt_key)
        if prompt is None:
            from src.ai.exception.prompt_exception import PromptNotFoundError
            raise PromptNotFoundError("提示词不存在", context={"prompt_key": request.prompt_key})
        content = self._renderer.render(prompt.template, request.variables)
        return PromptRenderResult(
            prompt_key=prompt.prompt_key,
            content=content,
            version=prompt.version,
            metadata=_loads_json(prompt.extra),
        )

    def list_templates(self, *, category: str | None = None) -> list[PromptData]:
        return self._get_store().list_enabled(category=category)

    def seed_defaults(self) -> int:
        """写入预置默认模板，已存在则跳过。

        Returns:
            新写入的模板数量
        """
        created = 0
        for key, (display_name, description, category, template) in _DEFAULT_TEMPLATES.items():
            try:
                existing = self._get_store().get_by_key(key, enabled_only=False)
                if existing is not None:
                    continue
                self.save_template(
                    prompt_key=key,
                    template=template,
                    display_name=display_name,
                    description=description,
                    category=category,
                )
                created += 1
                logger.info("已写入默认提示词模板: %s", key)
            except Exception:
                logger.warning("写入默认模板失败: %s", key, exc_info=True)
        return created


def _loads_json(value: str | None) -> dict:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


prompt_service = PromptService()
