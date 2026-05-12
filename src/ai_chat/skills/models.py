"""技能数据模型。"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SkillConfig:
    """单个技能定义。"""

    name: str
    description: str
    system_prompt: str
    tools: list[str] = field(default_factory=list)
    model: Optional[str] = None
    args_template: Optional[str] = None
    enabled: bool = True
    skill_dir: Optional[Path] = None

    @property
    def trigger(self) -> str:
        return f"/{self.name}"
