"""加载器注册表。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import LoaderStrategy

logger = logging.getLogger(__name__)


@dataclass
class LoaderEntry:
    """加载器注册条目。

    Attributes:
        loader_cls: 加载器类。
        priority: 优先级，数值越小越先执行。
        name: 加载器名称，默认取类名。
    """

    loader_cls: type[LoaderStrategy]
    priority: int
    name: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.loader_cls.__name__


class LoaderRegistry:
    """加载器注册表。

    新增加载器只需调用 register() 注册，ChainLoader 会自动发现。
    注册表按优先级排序，数值越小越先执行。

    使用方式::

        from src.ai.core.loaders.registry import loader_registry

        loader_registry.register(MyLoader, priority=150, name="my_loader")
    """

    def __init__(self) -> None:
        self._entries: list[LoaderEntry] = []
        self._sorted = True

    def register(
        self,
        loader_cls: type[LoaderStrategy],
        *,
        priority: int,
        name: str | None = None,
    ) -> None:
        """注册一个加载器类。

        Args:
            loader_cls: 加载器类，必须继承 LoaderStrategy。
            priority: 优先级，数值越小越先执行。
            name: 加载器名称，默认取类名。
        """
        entry = LoaderEntry(loader_cls=loader_cls, priority=priority, name=name)
        self._entries.append(entry)
        self._sorted = False
        logger.debug("已注册加载器: %s (优先级 %d)", entry.name, priority)

    def get_entries(self) -> list[LoaderEntry]:
        """返回按优先级排序的注册条目。"""
        if not self._sorted:
            self._entries.sort(key=lambda e: e.priority)
            self._sorted = True
        return list(self._entries)

    def clear(self) -> None:
        """清空注册表（主要用于测试）。"""
        self._entries.clear()
        self._sorted = True


loader_registry = LoaderRegistry()
