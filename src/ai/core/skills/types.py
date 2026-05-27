"""Skill 领域类型 — Agent Skills 开放标准。"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SkillDefinition:
    """标准 SKILL.md 技能定义。"""

    name: str
    description: str
    source_path: Path
    skill_dir: Path
    instruction_template: str
    disable_model_invocation: bool = False
    user_invocable: bool = True
    allowed_tools: list[str] = field(default_factory=list)
    argument_hint: str | None = None
    model: str | None = None
    context_fork: bool = False
    agent_type: str | None = None

    @property
    def is_auto_triggerable(self) -> bool:
        """是否可被模型自动激活。"""
        return not self.disable_model_invocation


@dataclass(frozen=True)
class SkillMetadata:
    """技能元数据 — Level 1 渐进式披露（~100 tokens）。"""

    name: str
    description: str
    argument_hint: str | None = None
    disable_model_invocation: bool = False
    user_invocable: bool = True
