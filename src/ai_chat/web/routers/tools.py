"""工具路由。"""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from src.ai_chat.web.deps import TEMPLATES
from src.ai_chat.web.services import (
    get_nav_items,
    get_tool_detail,
    list_tools_grouped,
    load_system_tools_action,
    scan_tools_action,
)

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_class=HTMLResponse, name="tools_page")
def tools_page(
    request: Request,
    name: str | None = None,
    flash_message: str | None = None,
    error_message: str | None = None,
) -> HTMLResponse:
    selected_tool = get_tool_detail(name) if name else None
    return TEMPLATES.TemplateResponse(
        request,
        "tools.html",
        {
            "request": request,
            "page_title": "工具",
            "page_subtitle": "查看、加载和扫描已注册的工具。",
            "nav_items": get_nav_items(),
            "current_page": "tools",
            "tool_groups": list_tools_grouped(),
            "selected_tool": selected_tool,
            "flash_message": flash_message,
            "error_message": error_message,
        },
    )


@router.post("/load-system", response_class=HTMLResponse)
def load_system_tools(request: Request) -> Response:
    try:
        count = load_system_tools_action()
        return RedirectResponse(
            url=f"/tools?{urlencode({'flash_message': f'已加载 {count} 个系统工具。'})}", status_code=303
        )
    except Exception as exc:
        return RedirectResponse(
            url=f"/tools?{urlencode({'error_message': f'加载系统工具失败：{exc}'})}", status_code=303
        )


@router.post("/scan", response_class=HTMLResponse)
def scan_tools(request: Request) -> Response:
    try:
        count = scan_tools_action()
        return RedirectResponse(
            url=f"/tools?{urlencode({'flash_message': f'扫描发现 {count} 个新工具。'})}", status_code=303
        )
    except Exception as exc:
        return RedirectResponse(
            url=f"/tools?{urlencode({'error_message': f'扫描工具失败：{exc}'})}", status_code=303
        )
