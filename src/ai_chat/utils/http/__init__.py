"""HTTP 工具包 — 客户端单例 + 实体转换管线。

导入此包即触发内置转换器注册。
"""

from src.ai_chat.utils.http.client import (
    HttpError,
    create_aclient,
    create_client,
    http_aclient,
    http_client,
)
from src.ai_chat.utils.http.converter import (
    ConverterError,
    ConverterRegistry,
    EntityConverter,
    converter_registry,
    register_converter,
)

# 触发内置转换器注册
import src.ai_chat.utils.http.converters  # noqa: F401

__all__ = [
    # 客户端
    "http_client",
    "http_aclient",
    "create_client",
    "create_aclient",
    "HttpError",
    # 转换器
    "EntityConverter",
    "ConverterError",
    "ConverterRegistry",
    "converter_registry",
    "register_converter",
]
