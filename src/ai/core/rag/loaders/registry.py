"""加载器注册表 — 基于类变量和类方法的自动注册。

加载器通过继承 ``LoaderStrategy`` 自动注册，无需装饰器或手动调用。
元数据（priority、name、settings_factory）声明为类变量。

用法::

    class MyLoader(LoaderStrategy):
        priority = 150
        name = "my_loader"
        ...

    # 获取所有已注册的加载器类
    for cls in LoaderRegistry.all():
        loader = cls()
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class LoaderRegistry:
    """加载器注册表（纯类方法）。

    通过 ``LoaderStrategy.__init_subclass__`` 自动收集所有具体加载器类。
    也可通过 ``register()`` 手动注册。

    Attributes:
        _registry: 已注册的加载器类列表（类变量，全局共享）。
    """

    _registry: list[type] = []

    @classmethod
    def register(cls, loader_cls: type) -> None:
        """注册一个加载器类。

        Args:
            loader_cls: 加载器类，必须继承 LoaderStrategy。
        """
        if loader_cls not in cls._registry:
            cls._registry.append(loader_cls)
            logger.debug(
                "已注册加载器: %s (优先级 %d)",
                loader_cls.name,
                loader_cls.priority,
            )

    @classmethod
    def all(cls) -> list[type]:
        """返回按优先级排序的所有已注册加载器类。"""
        return sorted(cls._registry, key=lambda c: c.priority)

    @classmethod
    def clear(cls) -> None:
        """清空注册表（主要用于测试）。"""
        cls._registry.clear()
