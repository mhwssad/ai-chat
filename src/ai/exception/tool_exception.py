"""统一工具层异常。"""


from src.ai.exception.base_exception import BaseExceptions


class ToolError(BaseExceptions):
    """工具层基础异常。"""


class ToolNotFoundError(ToolError):
    """工具不存在。"""


class ToolDisabledError(ToolError):
    """工具已禁用。"""


class ToolExecutionError(ToolError):
    """工具执行失败。"""


class ToolPermissionError(ToolError):
    """工具权限检查失败。"""
