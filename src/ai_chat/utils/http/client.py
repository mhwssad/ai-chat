"""项目通用 HTTP 客户端 — 基于 httpx 的单例封装，支持实体转换。

提供:
- http_client  — 同步客户端单例
- http_aclient — 异步客户端单例
- create_client()    — 创建自定义同步客户端
- create_aclient()   — 创建自定义异步客户端

默认超时读取 settings.request_timeout（60s），请求失败抛出 HttpError。
支持 response_type 参数自动反序列化响应，支持请求体自动序列化。
"""

from __future__ import annotations

import dataclasses
from typing import Any

import httpx
from pydantic import BaseModel

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.config.settings import settings
from src.ai_chat.utils.http.converter import (
    ConverterError,
    EntityConverter,
    converter_registry,
)

logger = get_logger(__name__)


# ── 异常 ─────────────────────────────────────────────────


class HttpError(Exception):
    """HTTP 请求失败异常。"""

    def __init__(
        self,
        message: str,
        *,
        url: str = "",
        method: str = "",
        status_code: int | None = None,
    ) -> None:
        self.url = url
        self.method = method
        self.status_code = status_code
        super().__init__(message)


# ── 基础设施 ─────────────────────────────────────────────

_DEFAULT_TIMEOUT = float(settings.request_timeout)


def _handle_response(response: httpx.Response) -> httpx.Response:
    """检查响应状态码，非 2xx 抛出 HttpError。"""
    if response.is_success:
        return response
    raise HttpError(
        f"HTTP {response.status_code}: {response.reason_phrase}",
        url=str(response.url),
        method=response.request.method,
        status_code=response.status_code,
    )


def _is_auto_serializable(obj: object) -> bool:
    """判断对象是否需要自动序列化（Pydantic 模型或 dataclass）。"""
    return isinstance(obj, BaseModel) or (
        dataclasses.is_dataclass(obj) and not isinstance(obj, type)
    )


def _prepare_request_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """预处理请求参数，自动序列化请求体中的 Pydantic 模型和 dataclass。"""
    kwargs = dict(kwargs)

    # json 参数：Pydantic/dataclass → dict（httpx 的 json 参数接受 dict 并自动 JSON 编码）
    json_data = kwargs.get("json")
    if json_data is not None and _is_auto_serializable(json_data):
        if isinstance(json_data, BaseModel):
            kwargs["json"] = json_data.model_dump(by_alias=True)
        elif dataclasses.is_dataclass(json_data):
            kwargs["json"] = dataclasses.asdict(json_data)  # type: ignore[arg-type]

    # content 参数：Pydantic/dataclass → 通过 converter_registry 序列化
    content_data = kwargs.get("content")
    if content_data is not None and not isinstance(content_data, (bytes, str, bytearray)):
        converter = converter_registry.find_for_request(content_data)
        if converter is not None:
            ct, body = converter.serialize(content_data)
            kwargs["content"] = body
            headers = kwargs.get("headers") or {}
            headers["Content-Type"] = ct
            kwargs["headers"] = headers
        else:
            raise ConverterError(
                f"无法序列化请求体类型: {type(content_data).__name__}",
                context={"data_type": type(content_data).__name__},
            )

    return kwargs


def _resolve_converter(
    response: httpx.Response,
    converter: str | EntityConverter | None,
) -> EntityConverter | None:
    """解析转换器实例。

    优先级: 显式 converter 参数 > content-type 匹配 > 默认转换器。
    """
    if converter is None:
        # 按 content-type 匹配
        ct = response.headers.get("content-type", "")
        conv = converter_registry.find_for_response(ct)
        if conv is not None:
            return conv
        # 回退到默认
        return converter_registry.get_default()

    if isinstance(converter, str):
        return converter_registry.get(converter)
    return converter


def _process_response(
    response: httpx.Response,
    *,
    response_type: type | None = None,
    converter: str | EntityConverter | None = None,
) -> httpx.Response | Any:
    """处理响应，按需反序列化。

    response_type=None 且 converter=None 时返回原始 Response（完全向后兼容）。
    """
    if response_type is None and converter is None:
        return response

    conv = _resolve_converter(response, converter)
    if conv is None:
        logger.debug("未找到匹配转换器，返回原始响应")
        return response

    try:
        return conv.deserialize(response, target_type=response_type)
    except Exception as e:
        raise ConverterError(
            f"响应反序列化失败: {e}",
            context={
                "converter": conv.name,
                "target_type": getattr(response_type, "__name__", None),
                "content_type": response.headers.get("content-type", ""),
            },
        ) from e


# ── 工厂函数 ─────────────────────────────────────────────


def create_client(
    base_url: str = "",
    headers: dict[str, str] | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
    **kwargs: Any,
) -> httpx.Client:
    """创建自定义同步 HTTP 客户端。"""
    opts: dict[str, Any] = {"headers": headers, "timeout": timeout, **kwargs}
    if base_url:
        opts["base_url"] = base_url
    return httpx.Client(**opts)


def create_aclient(
    base_url: str = "",
    headers: dict[str, str] | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
    **kwargs: Any,
) -> httpx.AsyncClient:
    """创建自定义异步 HTTP 客户端。"""
    opts: dict[str, Any] = {"headers": headers, "timeout": timeout, **kwargs}
    if base_url:
        opts["base_url"] = base_url
    return httpx.AsyncClient(**opts)


# ── 同步客户端包装 ───────────────────────────────────────


class _ClientWrapper:
    """同步客户端包装 — 延迟初始化，自动检查响应状态，支持实体转换。"""

    def __init__(self) -> None:
        self._client: httpx.Client | None = None

    def _ensure(self) -> httpx.Client:
        if self._client is None:
            self._client = create_client()
        return self._client

    def get(
        self,
        url: str,
        *,
        response_type: type | None = None,
        converter: str | EntityConverter | None = None,
        **kwargs: Any,
    ) -> httpx.Response | Any:
        kwargs = _prepare_request_kwargs(kwargs)
        response = _handle_response(self._ensure().get(url, **kwargs))
        return _process_response(response, response_type=response_type, converter=converter)

    def post(
        self,
        url: str,
        *,
        response_type: type | None = None,
        converter: str | EntityConverter | None = None,
        **kwargs: Any,
    ) -> httpx.Response | Any:
        kwargs = _prepare_request_kwargs(kwargs)
        response = _handle_response(self._ensure().post(url, **kwargs))
        return _process_response(response, response_type=response_type, converter=converter)

    def put(
        self,
        url: str,
        *,
        response_type: type | None = None,
        converter: str | EntityConverter | None = None,
        **kwargs: Any,
    ) -> httpx.Response | Any:
        kwargs = _prepare_request_kwargs(kwargs)
        response = _handle_response(self._ensure().put(url, **kwargs))
        return _process_response(response, response_type=response_type, converter=converter)

    def patch(
        self,
        url: str,
        *,
        response_type: type | None = None,
        converter: str | EntityConverter | None = None,
        **kwargs: Any,
    ) -> httpx.Response | Any:
        kwargs = _prepare_request_kwargs(kwargs)
        response = _handle_response(self._ensure().patch(url, **kwargs))
        return _process_response(response, response_type=response_type, converter=converter)

    def delete(
        self,
        url: str,
        *,
        response_type: type | None = None,
        converter: str | EntityConverter | None = None,
        **kwargs: Any,
    ) -> httpx.Response | Any:
        kwargs = _prepare_request_kwargs(kwargs)
        response = _handle_response(self._ensure().delete(url, **kwargs))
        return _process_response(response, response_type=response_type, converter=converter)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


# ── 异步客户端包装 ───────────────────────────────────────


class _AsyncClientWrapper:
    """异步客户端包装 — 延迟初始化，自动检查响应状态，支持实体转换。"""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    def _ensure(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = create_aclient()
        return self._client

    async def get(
        self,
        url: str,
        *,
        response_type: type | None = None,
        converter: str | EntityConverter | None = None,
        **kwargs: Any,
    ) -> httpx.Response | Any:
        kwargs = _prepare_request_kwargs(kwargs)
        response = _handle_response(await self._ensure().get(url, **kwargs))
        return _process_response(response, response_type=response_type, converter=converter)

    async def post(
        self,
        url: str,
        *,
        response_type: type | None = None,
        converter: str | EntityConverter | None = None,
        **kwargs: Any,
    ) -> httpx.Response | Any:
        kwargs = _prepare_request_kwargs(kwargs)
        response = _handle_response(await self._ensure().post(url, **kwargs))
        return _process_response(response, response_type=response_type, converter=converter)

    async def put(
        self,
        url: str,
        *,
        response_type: type | None = None,
        converter: str | EntityConverter | None = None,
        **kwargs: Any,
    ) -> httpx.Response | Any:
        kwargs = _prepare_request_kwargs(kwargs)
        response = _handle_response(await self._ensure().put(url, **kwargs))
        return _process_response(response, response_type=response_type, converter=converter)

    async def patch(
        self,
        url: str,
        *,
        response_type: type | None = None,
        converter: str | EntityConverter | None = None,
        **kwargs: Any,
    ) -> httpx.Response | Any:
        kwargs = _prepare_request_kwargs(kwargs)
        response = _handle_response(await self._ensure().patch(url, **kwargs))
        return _process_response(response, response_type=response_type, converter=converter)

    async def delete(
        self,
        url: str,
        *,
        response_type: type | None = None,
        converter: str | EntityConverter | None = None,
        **kwargs: Any,
    ) -> httpx.Response | Any:
        kwargs = _prepare_request_kwargs(kwargs)
        response = _handle_response(await self._ensure().delete(url, **kwargs))
        return _process_response(response, response_type=response_type, converter=converter)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# ── 全局单例 ─────────────────────────────────────────────

http_client = _ClientWrapper()
http_aclient = _AsyncClientWrapper()
