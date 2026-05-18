"""技能路由。"""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from src.ai_chat.web.deps import TEMPLATES
from src.ai_chat.web.services import (
    get_nav_items,
    get_skill_detail,
    list_all_skills,
    scan_skills_action,
    toggle_skill_action,
)

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_class=HTMLResponse, name="skills_page")
def skills_page(
    request: Request,
    name: str | None = None,
    flash_message: str | None = None,
    error_message: str | None = None,
) -> HTMLResponse:
    selected_skill = get_skill_detail(name) if name else None
    return TEMPLATES.TemplateResponse(
        request,
        "skills.html",
        {
            "request": request,
            "page_title": "技能",
            "nav_items": get_nav_items(),
            "current_page": "skills",
            "skills": list_all_skills(),
            "selected_skill": selected_skill,
            "flash_message": flash_message,
            "error_message": error_message,
        },
    )


@router.post("/scan", response_class=HTMLResponse)
def scan_skills(request: Request) -> Response:
    try:
        count = scan_skills_action()
        return RedirectResponse(
            url=f"/skills?{urlencode({'flash_message': f'扫描发现 {count} 个技能。'})}", status_code=303
        )
    except Exception as exc:
        return RedirectResponse(
            url=f"/skills?{urlencode({'error_message': f'扫描技能失败：{exc}'})}", status_code=303
        )


@router.post("/{skill_name}/toggle", response_class=HTMLResponse)
def toggle_skill(request: Request, skill_name: str) -> Response:
    try:
        enabled = toggle_skill_action(skill_name)
        state = "启用" if enabled else "禁用"
        return RedirectResponse(
            url=f"/skills?{urlencode({'name': skill_name, 'flash_message': f'技能已{state}。'})}",
            status_code=303,
        )
    except KeyError:
        return RedirectResponse(
            url=f"/skills?{urlencode({'error_message': '技能不存在。'})}", status_code=303
        )
    except Exception as exc:
        return RedirectResponse(
            url=f"/skills?{urlencode({'error_message': f'操作失败：{exc}'})}", status_code=303
        )
