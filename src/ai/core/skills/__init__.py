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
from src.ai.core.skills.loader import SkillLoader
from src.ai.core.skills.matcher import SkillMatcher
from src.ai.core.skills.service import SkillService
from src.ai.core.skills.types import SkillIndex


__all__ = [
    # 类型
    "SkillIndex",
    # 核心组件
    "SkillLoader",
    "SkillMatcher",
    "SkillService",
    # 异常
    "SkillError",
    "SkillLoadError",
    "SkillNotFoundError",
    "SkillRenderError",
]
