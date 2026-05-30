"""系统上下文收集器 — 收集环境信息（OS、工作目录、当前日期）。"""

import os
import platform
import sys
from datetime import datetime

from src.ai.core.context.collector import ContextCollector
from src.ai.core.context.types import (
    ContextBuildRequest,
    ContextCollectorResult,
    ContextSection,
)


class SystemCollector(ContextCollector):
    """收集系统环境信息。

    输出内容：操作系统、Shell、Python 版本、工作目录、当前日期。
    每次调用重新计算（不缓存）。
    """

    @property
    def name(self) -> str:
        return "system"

    async def collect(self, request: ContextBuildRequest) -> ContextCollectorResult:
        parts = [
            f"Platform: {platform.system()} {platform.release()}",
            f"Shell: {os.environ.get('SHELL', 'unknown')}",
            f"Python: {sys.version.split()[0]}",
            f"CWD: {os.getcwd()}",
            f"Date: {datetime.now().strftime('%Y-%m-%d')}",
        ]
        content = "\n".join(parts)
        section = ContextSection(
            name="system_env",
            content=content,
            priority=0,  # 最高优先级
            cacheable=False,  # 日期每次不同
        )
        return ContextCollectorResult(sections=[section])
