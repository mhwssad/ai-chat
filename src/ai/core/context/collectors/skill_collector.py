"""技能索引收集器 — 注入技能名称、描述和文件路径到上下文。

AI 通过上下文中的索引进行语义匹配，判定需要时使用文件读取工具
直接读取对应 SKILL.md 的完整内容。
"""

from src.ai.config.logging_setup import get_logger
from typing import TYPE_CHECKING

from src.ai.core.context.collector import ContextCollector
from src.ai.core.context.types import (
    ContextBuildRequest,
    ContextCollectorResult,
    ContextSection,
)

if TYPE_CHECKING:
    from src.ai.core.skills.service import SkillService

logger = get_logger(__name__)


class SkillCollector(ContextCollector):
    """收集技能索引上下文。

    注入所有可自动触发的技能名称、描述和文件路径。
    AI 判断需要某技能时，使用文件读取工具查看 SKILL.md 完整内容。

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
            indices = [
                idx
                for idx in self._skill_service.list_auto_triggerable()
                if not idx.disable_model_invocation
            ]

            if not indices:
                return ContextCollectorResult()

            lines = ["## 可用技能", ""]
            for idx in indices:
                hint = f" (参数: {idx.argument_hint})" if idx.argument_hint else ""
                lines.append(
                    f"- **{idx.name}**: {idx.description}{hint}"
                    f"  → `{idx.source_path}`"
                )

            lines.extend(
                [
                    "",
                    "需要使用某技能时，使用文件读取工具查看对应 SKILL.md 获取完整指令。",
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
            logger.debug("技能索引收集失败", exc_info=True)
            return ContextCollectorResult()
