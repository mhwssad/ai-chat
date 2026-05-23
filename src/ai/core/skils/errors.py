"""Skill 模块异常。"""

from src.ai.exception.base_exception import BaseExceptions


class SkillError(BaseExceptions):
    """Skill 基础异常。"""


class SkillLoadError(SkillError):
    """Skill 加载失败。"""


class SkillRenderError(SkillError):
    """Skill 渲染失败。"""

