"""记忆模块异常。"""

from src.ai.exception.base_exception import BaseExceptions


class MemoryException(BaseExceptions):
    """记忆模块基础异常。"""


class MemoryPathError(MemoryException):
    """记忆路径不安全或无效。"""


class MemoryNotFoundError(MemoryException):
    """记忆条目不存在。"""


class MemoryScanError(MemoryException):
    """记忆扫描失败。"""
