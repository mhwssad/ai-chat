"""技能元数据收集器 — 收集技能信息（Level 1 渐进式披露）。"""

import logging
from typing import TYPE_CHECKING

from src.ai.core.context.collector import ContextCollector
from src.ai.core.context.types import (
    ContextBuildRequest,
    ContextCollectorResult,
    ContextSection,
)

if TYPE_CHECKING:
    from src.ai.core.skills.service import SkillService

logger = logging.getLogger(__name__)


class SkillCollector(ContextCollector):
    """收集技能元数据上下文。

    列出所有可自动触发的技能名称和描述（Level 1 渐进式披露）。
    可缓存（技能列表变化不频繁）。

    Args:
        skill_service: 技能服务实例。
    """

    def __init__(self, skill_service: "SkillService") -> None:
        self._skill_service = skill_service

    @property
    def name(self) -> str:
        return "skills"

    async def collect(self, request: ContextBuildRequest) -> ContextCollectorResult:
        if not request.enable_tools:
            return ContextCollectorResult()

        try:
            # 获取所有技能元数据，过滤可自动触发的
            all_metadata = self._skill_service.get_skill_metadata()
            auto_triggerable = [
                m for m in all_metadata if not m.disable_model_invocation
            ]

            if not auto_triggerable:
                return ContextCollectorResult()

            lines = ["## 可用技能", ""]
            for meta in auto_triggerable:
                hint = f" (参数: {meta.argument_hint})" if meta.argument_hint else ""
                lines.append(f"- {meta.name}: {meta.description}{hint}")

            lines.extend(
                [
                    "",
                    "使用 skill 工具激活技能: skill(name='技能名', arguments='参数')",
                ]
            )

            section = ContextSection(
                name="skills",
                content="\n".join(lines),
                priority=3,
                cacheable=True,
            )
            return ContextCollectorResult(sections=[section])
        except Exception:
            logger.debug("技能元数据收集失败", exc_info=True)
            return ContextCollectorResult()
