"""提示词异常。"""

from src.ai.exception.base_exception import BaseExceptions


class PromptError(BaseExceptions):
    """提示词基础异常。"""


class PromptNotFoundError(PromptError):
    """提示词不存在。"""


class PromptRenderError(PromptError):
    """提示词渲染失败。"""

