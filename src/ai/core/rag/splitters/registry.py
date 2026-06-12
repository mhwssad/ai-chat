"""切割器注册表。"""

from __future__ import annotations

from src.ai.config.logging_setup import get_logger
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

    from .base import SplitterStrategy

logger = get_logger(__name__)

# 元数据属性名
_SPLITTER_PRIORITY_ATTR = "__splitter_priority__"
_SPLITTER_NAME_ATTR = "__splitter_name__"


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


def register_splitter(*, priority: int = 500, name: str = ""):
    """装饰器：标记切割器类的注册元数据。

    不依赖任何 registry 实例，仅设置类属性。
    由 SplitterRegistry.discover() 在运行时发现并注册。

    Args:
        priority: 优先级，数值越小越先执行。
        name: 切割器名称，默认取类名。

    Usage::

        @register_splitter(priority=100, name="markdown")
        class MarkdownSplitter(SplitterStrategy): ...
    """

    def decorator(cls: type) -> type:
        setattr(cls, _SPLITTER_PRIORITY_ATTR, priority)
        setattr(cls, _SPLITTER_NAME_ATTR, name or cls.__name__)
        return cls

    return decorator


class SplitterRegistry:
    """切割器注册表。

    新增切割器使用 ``@register_splitter`` 装饰器标记，
    再由 ``SplitterRegistry.discover()`` 自动发现并注册。

    也可手动调用 ``register()`` 直接注册。
    """

    def __init__(self) -> None:
        self._entries: list[SplitterEntry] = []
        self._sorted = True

    @classmethod
    def discover(cls, modules: list[ModuleType]) -> SplitterRegistry:
        """从已导入的模块中发现带 ``@register_splitter`` 标记的类并注册。

        Args:
            modules: 要扫描的模块列表。

        Returns:
            包含所有已发现切割器的注册表实例。
        """
        from .base import SplitterStrategy

        registry = cls()
        for mod in modules:
            for attr_name in dir(mod):
                obj = getattr(mod, attr_name, None)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, SplitterStrategy)
                    and hasattr(obj, _SPLITTER_PRIORITY_ATTR)
                ):
                    registry.register(
                        obj,
                        priority=getattr(obj, _SPLITTER_PRIORITY_ATTR),
                        name=getattr(obj, _SPLITTER_NAME_ATTR),
                    )
        return registry

    def register(
        self,
        splitter_cls: type[SplitterStrategy],
        *,
        priority: int,
        name: str | None = None,
    ) -> None:
        """手动注册一个切割器类。

        Args:
            splitter_cls: 切割器类，必须继承 SplitterStrategy。
            priority: 优先级，数值越小越先执行。
            name: 切割器名称，默认取类名。
        """
        entry = SplitterEntry(
            splitter_cls=splitter_cls,
            priority=priority,
            name=name or splitter_cls.__name__,
        )
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
