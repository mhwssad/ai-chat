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
    priority: int = 0
    skill_dir: Optional[Path] = None

    def __post_init__(self) -> None:
        # 缓存 trigger，避免每次属性访问都拼接字符串
        self._trigger = f"/{self.name}"

    @property
    def trigger(self) -> str:
        return self._trigger
