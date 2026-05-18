"""记忆路由。"""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from src.ai_chat.web.deps import TEMPLATES
from src.ai_chat.web.services import (
    delete_memory_session,
    get_memory_context_info,
    get_memory_session_detail,
    get_nav_items,
    list_memory_sessions,
    rename_memory_session,
    reset_memory_session,
    search_memory_sessions,
)

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("", response_class=HTMLResponse, name="memory_page")
def memory_page(
    request: Request,
    session_id: str | None = None,
    keyword: str | None = None,
    flash_message: str | None = None,
    error_message: str | None = None,
) -> HTMLResponse:
    if keyword:
        sessions = search_memory_sessions(keyword)
    else:
        sessions = list_memory_sessions()
    selected_session = get_memory_session_detail(session_id) if session_id else None
    context_info = get_memory_context_info(session_id) if session_id else None
    usage_capped = min(context_info.usage_percent, 100) if context_info else 0
    return TEMPLATES.TemplateResponse(
        request,
        "memory.html",
        {
            "request": request,
            "page_title": "记忆",
            "nav_items": get_nav_items(),
            "current_page": "memory",
            "sessions": sessions,
            "selected_session": selected_session,
            "context_info": context_info,
            "usage_capped": usage_capped,
            "search_keyword": keyword or "",
            "flash_message": flash_message,
            "error_message": error_message,
        },
    )


@router.post("/{session_id}/rename", response_class=HTMLResponse)
def rename_session(
    request: Request, session_id: str, title: str = Form(...)
) -> Response:
    new_title = title.strip()
    if not new_title:
        return RedirectResponse(
            url=f"/memory?{urlencode({'session_id': session_id, 'error_message': '标题不能为空。'})}",
            status_code=303,
        )
    try:
        rename_memory_session(session_id, new_title)
    except Exception as exc:
        return RedirectResponse(
            url=f"/memory?{urlencode({'session_id': session_id, 'error_message': f'重命名失败：{exc}'})}",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/memory?{urlencode({'session_id': session_id, 'flash_message': '会话已重命名。'})}",
        status_code=303,
    )


@router.post("/{session_id}/reset", response_class=HTMLResponse)
def reset_session(request: Request, session_id: str) -> Response:
    try:
        reset_memory_session(session_id)
    except Exception as exc:
        return RedirectResponse(
            url=f"/memory?{urlencode({'session_id': session_id, 'error_message': f'重置失败：{exc}'})}",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/memory?{urlencode({'session_id': session_id, 'flash_message': '会话已重置，消息和摘要已清空。'})}",
        status_code=303,
    )


@router.post("/{session_id}/delete", response_class=HTMLResponse)
def delete_session(request: Request, session_id: str) -> Response:
    try:
        delete_memory_session(session_id)
    except Exception as exc:
        return RedirectResponse(
            url=f"/memory?{urlencode({'error_message': f'删除失败：{exc}'})}", status_code=303
        )
    return RedirectResponse(url=f"/memory?{urlencode({'flash_message': '会话已删除。'})}", status_code=303)
