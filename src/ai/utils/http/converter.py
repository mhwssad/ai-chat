"""实体转换器核心 — ABC 基类、注册表和装饰器。

提供:
- EntityConverter    — 转换器策略 ABC
- ConverterRegistry — 注册表（按名查找 + content-type 匹配）
- register_converter — 类装饰器，自动注册到全局 registry
- converter_registry — 全局单例

参考 memory factory 的 ABC + dict 注册表 + 装饰器 + 单例模式。
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

import httpx

from src.ai.config.logging_setup import get_logger
from src.ai.exception.http_exception import ConverterError

logger = get_logger(__name__)


# ── ABC ──────────────────────────────────────────────────


class EntityConverter(ABC):
    """实体转换器策略基类。

    所有自定义转换器须继承此类，实现 serialize/deserialize 方法，
    并设置 name 和 content_types 类变量。

    子类通过 @register_converter 装饰器自动注册到全局 converter_registry。
    """

    name: ClassVar[str]
    content_types: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    def can_handle_response(self, content_type: str) -> bool:
        """判断是否能处理给定的响应 content-type。

        Args:
            content_type: HTTP 响应的 Content-Type 头值。
        """

    @abstractmethod
    def can_handle_request(self, data: object) -> bool:
        """判断是否能序列化给定的请求体对象。

        Args:
            data: 待序列化的 Python 对象。
        """

    @abstractmethod
    def deserialize(
        self,
        response: httpx.Response,
        target_type: type | None = None,
    ) -> Any:
        """将 httpx.Response 反序列化为目标类型。

        Args:
            response: httpx 原始响应。
            target_type: 期望的返回类型，None 时返回转换器默认类型。
        """

    @abstractmethod
    def serialize(self, data: object) -> tuple[str, bytes]:
        """将 Python 对象序列化为请求体。

        Returns:
            (content_type, body_bytes) 元组。
        """


# ── 注册表 ───────────────────────────────────────────────


class ConverterRegistry:
    """转换器注册表。

    按 name 注册 EntityConverter 实例，
    支持按 content-type 和数据类型自动匹配转换器。
    """

    def __init__(self) -> None:
        self._registry: dict[str, EntityConverter] = {}
        self._default_name: str | None = None

    def register(
        self,
        converter: EntityConverter,
        *,
        default: bool = False,
    ) -> None:
        """注册转换器实例。

        Args:
            converter: EntityConverter 实例。
            default: 是否设为默认转换器。
        """
        self._registry[converter.name] = converter
        if default:
            self._default_name = converter.name
        logger.debug(
            "已注册转换器: '%s'%s", converter.name, " (默认)" if default else ""
        )

    def get(self, name: str) -> EntityConverter:
        """按名称获取转换器。

        Raises:
            ConverterError: 名称未注册时抛出。
        """
        converter = self._registry.get(name)
        if converter is None:
            raise ConverterError(
                f"未找到转换器: '{name}'",
                context={"available": list(self._registry)},
            )
        return converter

    def find_for_response(self, content_type: str) -> EntityConverter | None:
        """按响应 content-type 查找匹配的转换器。

        Args:
            content_type: 响应头中的 Content-Type 值（可含 charset 等后缀）。
        """
        mime = content_type.split(";", 1)[0].strip().lower()
        for converter in self._registry.values():
            if converter.can_handle_response(mime):
                return converter
        return None

    def find_for_request(self, data: object) -> EntityConverter | None:
        """按请求数据类型查找匹配的转换器。"""
        for converter in self._registry.values():
            if converter.can_handle_request(data):
                return converter
        return None

    def get_default(self) -> EntityConverter | None:
        """获取默认转换器。"""
        if self._default_name is None:
            return None
        return self._registry.get(self._default_name)

    def list_converters(self) -> list[str]:
        """返回所有已注册的转换器名称。"""
        return list(self._registry)


# ── 装饰器 ───────────────────────────────────────────────


def register_converter(name: str, *, default: bool = False):
    """类装饰器：将 EntityConverter 子类实例化并注册到全局 registry。

    用法::

        @register_converter("json", default=True)
        class JsonConverter(EntityConverter):
            ...

    Args:
        name: 转换器唯一标识名。
        default: 是否设为默认转换器。
    """

    def decorator(cls: type[EntityConverter]) -> type[EntityConverter]:
        instance = cls()
        converter_registry.register(instance, default=default)
        return cls

    return decorator


# ── 全局单例 ─────────────────────────────────────────────

converter_registry = ConverterRegistry()
