"""SPA 回退中间件 — 支持 Vue Router HTML5 history 模式。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, Response


class SPAFallbackMiddleware(BaseHTTPMiddleware):
    """SPA 前端回退中间件。

    规则：
    1. /api/*、/docs、/openapi → 透传 FastAPI 路由
    2. dist 目录中存在的静态文件 → 返回文件
    3. 其他路径 → 返回 index.html（Vue Router 客户端路由）
    """

    def __init__(self, app: Any, dist_dir: str | Path) -> None:
        super().__init__(app)
        self._dist = Path(dist_dir).resolve()
        self._index = self._dist / "index.html"

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path

        # API 和文档路径透传
        if (
            path.startswith("/api/")
            or path.startswith("/docs")
            or path.startswith("/openapi")
        ):
            return await call_next(request)

        # 尝试匹配静态文件
        file_path = self._dist / path.lstrip("/")
        if file_path.is_file() and ".." not in path:
            return FileResponse(file_path)

        # SPA 回退：返回 index.html
        if self._index.is_file():
            return FileResponse(self._index)

        # 前端未构建时回退到 FastAPI 路由
        return await call_next(request)
