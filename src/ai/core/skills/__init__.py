"""Skill 上下文注入模块 — Agent Skills 开放标准。

Skills 是可安装、可复用的标准化指令包，通过注入到 AI
对话上下文来改变模型行为。遵循 agentskills.io 规范。
"""

from src.ai.exception.skill_exception import (
    SkillError,
    SkillLoadError,
    SkillNotFoundError,
    SkillRenderError,
)
from src.ai.core.skills.loader import SkillLoader, split_frontmatter
from src.ai.core.skills.renderer import SkillRenderer
from src.ai.core.skills.service import SkillService, skill_service
from src.ai.core.skills.types import SkillDefinition, SkillMetadata

__all__ = [
    # 类型
    "SkillDefinition",
    "SkillMetadata",
    # 核心组件
    "SkillLoader",
    "SkillRenderer",
    "SkillService",
    "skill_service",
    "split_frontmatter",
    # 异常
    "SkillError",
    "SkillLoadError",
    "SkillNotFoundError",
    "SkillRenderError",
]
