"""切割器注册表。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import SplitterStrategy

logger = logging.getLogger(__name__)


@dataclass
class SplitterEntry:
    """切割器注册条目。

    Attributes:
        splitter_cls: 切割器类。
        priority: 优先级，数值越小越先执行。
        name: 切割器名称，默认取类名。
    """

    splitter_cls: type[SplitterStrategy]
    priority: int
    name: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.splitter_cls.__name__


class SplitterRegistry:
    """切割器注册表。

    新增切割器只需调用 register() 注册，ChainSplitter 会自动发现。

    使用方式::

        from src.ai.core.splitters.registry import splitter_registry

        splitter_registry.register(MySplitter, priority=150, name="my_splitter")
    """

    def __init__(self) -> None:
        self._entries: list[SplitterEntry] = []
        self._sorted = True

    def register(
        self,
        splitter_cls: type[SplitterStrategy],
        *,
        priority: int,
        name: str | None = None,
    ) -> None:
        """注册一个切割器类。

        Args:
            splitter_cls: 切割器类，必须继承 SplitterStrategy。
            priority: 优先级，数值越小越先执行。
            name: 切割器名称，默认取类名。
        """
        entry = SplitterEntry(splitter_cls=splitter_cls, priority=priority, name=name)
        self._entries.append(entry)
        self._sorted = False
        logger.debug("已注册切割器: %s (优先级 %d)", entry.name, priority)

    def get_entries(self) -> list[SplitterEntry]:
        """返回按优先级排序的注册条目。"""
        if not self._sorted:
            self._entries.sort(key=lambda e: e.priority)
            self._sorted = True
        return list(self._entries)

    def clear(self) -> None:
        """清空注册表。"""
        self._entries.clear()
        self._sorted = True


splitter_registry = SplitterRegistry()
