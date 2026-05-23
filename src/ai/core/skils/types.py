"""Skill 领域类型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SkillDefinition:
    """从 SKILL.md 解析出的技能定义。"""

    skill_key: str
    display_name: str | None
    description: str
    version: str | None
    source_path: Path
    prompt: str
    capabilities: list[str] = field(default_factory=list)
    input_schema: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def tool_name(self) -> str:
        return f"skill.{self.skill_key}"

