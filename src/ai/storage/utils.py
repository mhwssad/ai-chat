"""存储层公共工具。"""

from datetime import datetime


def dt_now() -> datetime:
    """返回当前本地时间（无时区信息）。"""
    return datetime.now()
