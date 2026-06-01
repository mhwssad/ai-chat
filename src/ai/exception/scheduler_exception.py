"""定时任务层异常。"""

from src.ai.exception.base_exception import BaseExceptions


class SchedulerError(BaseExceptions):
    """定时任务层基础异常。"""


class SchedulerNotFoundError(SchedulerError):
    """任务不存在。"""
