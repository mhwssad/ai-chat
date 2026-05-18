"""MCP 路由。"""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from src.ai_chat.web.deps import TEMPLATES
from src.ai_chat.web.services import (
    get_mcp_server_configs,
    get_mcp_status,
    get_nav_items,
    initialize_mcp_client,
    list_mcp_tools,
    shutdown_mcp_client,
)

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("", response_class=HTMLResponse, name="mcp_page")
def mcp_page(
    request: Request,
    flash_message: str | None = None,
    error_message: str | None = None,
) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(
        request,
        "mcp.html",
        {
            "request": request,
            "page_title": "MCP",
            "nav_items": get_nav_items(),
            "current_page": "mcp",
            "status": get_mcp_status(),
            "server_configs": get_mcp_server_configs(),
            "mcp_tools": list_mcp_tools(),
            "flash_message": flash_message,
            "error_message": error_message,
        },
    )


@router.post("/initialize", response_class=HTMLResponse)
def initialize_mcp(request: Request) -> Response:
    try:
        count = initialize_mcp_client()
        return RedirectResponse(
            url=f"/mcp?{urlencode({'flash_message': f'MCP 客户端已初始化，加载 {count} 个工具。'})}",
            status_code=303,
        )
    except Exception as exc:
        return RedirectResponse(
            url=f"/mcp?{urlencode({'error_message': f'初始化失败：{exc}'})}", status_code=303
        )


@router.post("/shutdown", response_class=HTMLResponse)
def shutdown_mcp(request: Request) -> Response:
    try:
        shutdown_mcp_client()
        return RedirectResponse(
            url=f"/mcp?{urlencode({'flash_message': 'MCP 客户端已关闭。'})}", status_code=303
        )
    except Exception as exc:
        return RedirectResponse(
            url=f"/mcp?{urlencode({'error_message': f'关闭失败：{exc}'})}", status_code=303
        )
