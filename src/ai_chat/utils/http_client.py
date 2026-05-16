from __future__ import annotations

"""项目通用 HTTP 客户端 — 基于 httpx 的单例封装。

提供:
- http_client  — 同步客户端单例
- http_aclient — 异步客户端单例
- create_client()    — 创建自定义同步客户端
- create_aclient()   — 创建自定义异步客户端

默认超时读取 settings.request_timeout（60s），请求失败抛出 BaseExceptions。
"""

from typing import Any, Optional

import httpx

from src.ai_chat.config.base_exception import BaseExceptions
from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.config.settings import settings

logger = get_logger(__name__)


class HttpError(BaseExceptions):
    """HTTP 请求失败异常。"""

    def __init__(
        self,
        message: str,
        *,
        url: str = "",
        method: str = "",
        status_code: int | None = None,
    ) -> None:
        context: dict[str, Any] = {}
        if url:
            context["url"] = url
        if method:
            context["method"] = method
        if status_code is not None:
            context["status_code"] = status_code
        super().__init__(message, context=context)


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


# ── 单例客户端 ────────────────────────────────────────

class _ClientWrapper:
    """同步客户端包装 — 延迟初始化，自动检查响应状态。"""

    def __init__(self) -> None:
        self._client: httpx.Client | None = None

    def _ensure(self) -> httpx.Client:
        if self._client is None:
            self._client = create_client()
        return self._client

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return _handle_response(self._ensure().get(url, **kwargs))

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return _handle_response(self._ensure().post(url, **kwargs))

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return _handle_response(self._ensure().put(url, **kwargs))

    def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        return _handle_response(self._ensure().patch(url, **kwargs))

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return _handle_response(self._ensure().delete(url, **kwargs))

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


class _AsyncClientWrapper:
    """异步客户端包装 — 延迟初始化，自动检查响应状态。"""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    def _ensure(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = create_aclient()
        return self._client

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return _handle_response(await self._ensure().get(url, **kwargs))

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return _handle_response(await self._ensure().post(url, **kwargs))

    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return _handle_response(await self._ensure().put(url, **kwargs))

    async def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        return _handle_response(await self._ensure().patch(url, **kwargs))

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return _handle_response(await self._ensure().delete(url, **kwargs))

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


http_client = _ClientWrapper()
http_aclient = _AsyncClientWrapper()
