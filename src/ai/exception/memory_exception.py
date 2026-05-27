"""记忆模块异常。"""

from src.ai.exception.base_exception import BaseExceptions


class MemoryError(BaseExceptions):
    """记忆模块基础异常。"""


class MemoryPathError(MemoryError):
    """记忆路径不安全或无效。"""


class MemoryScanError(MemoryError):
    """记忆扫描失败。"""
