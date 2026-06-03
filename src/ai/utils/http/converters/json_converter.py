"""内置 JSON 转换器 — 处理 application/json 的序列化与反序列化。

支持:
- 请求: dict / list / BaseModel / dataclass → JSON bytes
- 响应: JSON → dict / list / BaseModel 实例
"""

import dataclasses
import json
from typing import Any, ClassVar

import httpx
from pydantic import BaseModel

from src.ai.config.logging_setup import get_logger
from src.ai.utils.http.converter import EntityConverter, register_converter

logger = get_logger(__name__)


def _is_pydantic_model(obj: object) -> bool:
    return isinstance(obj, BaseModel) or (
        isinstance(obj, type) and issubclass(obj, BaseModel)
    )


def _is_dataclass(obj: object) -> bool:
    return dataclasses.is_dataclass(obj) and not isinstance(obj, type)


def _to_plain_dict(data: object) -> Any:
    """将 BaseModel / dataclass 递归转为可 JSON 序列化的 dict/list。"""
    if isinstance(data, BaseModel):
        return data.model_dump(by_alias=True)
    if _is_dataclass(data):
        return dataclasses.asdict(data)  # type: ignore[call-overload]
    return data


@register_converter("json", default=True)
class JsonConverter(EntityConverter):
    """内置 JSON 转换器。"""

    name: ClassVar[str] = "json"
    content_types: ClassVar[tuple[str, ...]] = ("application/json",)

    def can_handle_response(self, content_type: str) -> bool:
        return content_type == "application/json"

    def can_handle_request(self, data: object) -> bool:
        return (
            isinstance(data, (dict, list))
            or _is_pydantic_model(data)
            or _is_dataclass(data)
        )

    def deserialize(
        self,
        response: httpx.Response,
        target_type: type | None = None,
    ) -> Any:
        if (
            target_type is not None
            and isinstance(target_type, type)
            and issubclass(target_type, BaseModel)
        ):
            return target_type.model_validate_json(response.content)
        return response.json()

    def serialize(self, data: object) -> tuple[str, bytes]:
        plain = _to_plain_dict(data)
        body = json.dumps(plain, ensure_ascii=False).encode("utf-8")
        return "application/json", body
