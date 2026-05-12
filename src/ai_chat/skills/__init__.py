"""技能模块 — 自动扫描 skills/ 目录下的 .md 文件。"""

from pathlib import Path

from .registry import skill_registry, registered_skill
from .models import SkillConfig
from .menu import menu_skills

skill_registry.scan(Path(__file__).parent / "skills")

__all__ = [
    "skill_registry",
    "registered_skill",
    "SkillConfig",
    "menu_skills",
]
