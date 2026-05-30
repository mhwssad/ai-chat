"""上下文收集器接口和并行协调器。"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from src.ai.core.context.types import (
    ContextBuildRequest,
    ContextCollectorResult,
    ContextSection,
)

logger = logging.getLogger(__name__)


class ContextCollector(ABC):
    """上下文收集器接口。

    所有上下文源实现此接口，由 ContextCoordinator 并行调度。
    """

    @abstractmethod
    async def collect(self, request: ContextBuildRequest) -> ContextCollectorResult:
        """收集上下文数据。

        Args:
            request: 上下文构建请求。

        Returns:
            收集结果（段列表 + token 估算）。
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """收集器名称（用于日志和调试）。"""


class ContextCoordinator:
    """上下文协调器 — 并行获取所有收集器结果。

    Args:
        collectors: 收集器列表。
    """

    def __init__(self, collectors: list[ContextCollector]) -> None:
        self._collectors = collectors

    async def collect_all(self, request: ContextBuildRequest) -> list[ContextSection]:
        """并行执行所有收集器，合并结果并按 priority 排序。

        单个收集器失败不影响其他收集器。

        Args:
            request: 上下文构建请求。

        Returns:
            按 priority 排序的上下文段列表。
        """
        import asyncio

        tasks = [c.collect(request) for c in self._collectors]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        sections: list[ContextSection] = []
        for collector, result in zip(self._collectors, results):
            if isinstance(result, Exception):
                logger.warning(
                    "收集器 %s 失败: %s", collector.name, result, exc_info=result
                )
                continue
            sections.extend(result.sections)

        sections.sort(key=lambda s: s.priority)
        return sections
