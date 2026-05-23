"""Skill 核心能力。

注意：目录名沿用当前项目中的 `skils`。对外能力以 SkillService 为入口。
"""

from src.ai.core.skils.errors import SkillError, SkillLoadError, SkillRenderError
from src.ai.core.skils.loader import SkillLoader, split_frontmatter
from src.ai.core.skils.renderer import SkillRenderer
from src.ai.core.skils.service import SkillService, skill_service
from src.ai.core.skils.types import SkillDefinition

__all__ = [
    "SkillDefinition",
    "SkillError",
    "SkillLoadError",
    "SkillLoader",
    "SkillRenderError",
    "SkillRenderer",
    "SkillService",
    "skill_service",
    "split_frontmatter",
]
