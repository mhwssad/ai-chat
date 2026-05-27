"""内置表单转换器 — 处理 application/x-www-form-urlencoded 的序列化与反序列化。

支持:
- 请求: dict / BaseModel → form-encoded bytes
- 响应: form-encoded → dict
"""


from typing import Any, ClassVar
from urllib.parse import parse_qs, urlencode

import httpx
from pydantic import BaseModel

from src.ai.config.logging_setup import get_logger
from src.ai.utils.http.converter import EntityConverter, register_converter

logger = get_logger(__name__)


@register_converter("form")
class FormConverter(EntityConverter):
    """内置表单转换器。"""

    name: ClassVar[str] = "form"
    content_types: ClassVar[tuple[str, ...]] = ("application/x-www-form-urlencoded",)

    def can_handle_response(self, content_type: str) -> bool:
        return content_type == "application/x-www-form-urlencoded"

    def can_handle_request(self, data: object) -> bool:
        if isinstance(data, dict):
            return all(isinstance(v, (str, int, float, bool)) for v in data.values())
        if isinstance(data, BaseModel):
            return True
        return False

    def deserialize(
        self,
        response: httpx.Response,
        target_type: type | None = None,
    ) -> Any:
        parsed = parse_qs(response.text, keep_blank_values=True)
        # parse_qs 返回 list 值，展平单值项
        return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}

    def serialize(self, data: object) -> tuple[str, bytes]:
        if isinstance(data, BaseModel):
            plain = data.model_dump(by_alias=True)
        elif isinstance(data, dict):
            plain = data
        else:
            plain = dict(data)  # type: ignore[arg-type]
        body = urlencode(plain, doseq=True).encode("utf-8")
        return "application/x-www-form-urlencoded", body
