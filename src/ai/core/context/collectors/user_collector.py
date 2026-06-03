"""用户上下文收集器 — 从 DB 模板收集系统提示词。"""

import logging
from typing import Any

from src.ai.core.context.collector import ContextCollector
from src.ai.core.context.types import (
    ContextBuildRequest,
    ContextCollectorResult,
    ContextSection,
)

logger = logging.getLogger(__name__)


class UserCollector(ContextCollector):
    """收集用户系统提示词。

    优先使用 custom_system_prompt，其次从 DB 模板加载。
    可缓存（会话内不变）。
    """

    def __init__(self, prompt_service: Any) -> None:
        self._prompt_service = prompt_service

    @property
    def name(self) -> str:
        return "user"

    async def collect(self, request: ContextBuildRequest) -> ContextCollectorResult:
        content = request.custom_system_prompt or self._load_from_db()

        section = ContextSection(
            name="system_prompt",
            content=content,
            priority=0,
            cacheable=True,
        )
        return ContextCollectorResult(sections=[section])

    def _load_from_db(self) -> str:
        """从 DB 加载系统提示词模板。"""
        from src.ai.core.prompts.types import PromptRenderRequest

        result = self._prompt_service.render(
            PromptRenderRequest(prompt_key="chat.system_prompt", variables={})
        )
        return result.content
