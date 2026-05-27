"""Skill 模块异常。"""

from src.ai.exception.base_exception import BaseExceptions


class SkillError(BaseExceptions):
    """Skill 基础异常。"""


class SkillLoadError(SkillError):
    """Skill 加载失败（文件不存在、解析错误）。"""


class SkillRenderError(SkillError):
    """Skill 渲染失败（模板渲染、动态命令执行错误）。"""


class SkillNotFoundError(SkillError):
    """Skill 不存在。"""
