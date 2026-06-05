"""线程池异常定义。

提供线程池管理相关的异常层次结构。
"""

from src.ai.exception.base_exception import BaseExceptions


class ThreadPoolError(BaseExceptions):
    """线程池相关异常基类。"""


class ThreadPoolShutdownError(ThreadPoolError):
    """线程池已关闭时提交任务。"""


class ThreadPoolTimeoutError(ThreadPoolError):
    """线程池优雅关闭超时。"""
