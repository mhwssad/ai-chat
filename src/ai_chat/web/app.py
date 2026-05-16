"""FastAPI + Jinja2 Web 入口。"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.ai_chat.memory.models import SessionNotFoundException
from src.ai_chat.web.services import (
    AgentName,
    default_model_name,
    ensure_session_exists,
    get_agent_options,
    get_nav_items,
    list_recent_sessions,
    load_session_messages,
    normalize_agent_name,
    placeholder_copy,
    send_chat_message,
    create_chat_session,
)


WEB_DIR = Path(__file__).parent
TEMPLATES = Jinja2Templates(directory=str(WEB_DIR / "templates"))


def create_app() -> FastAPI:
    app = FastAPI(title="AI Chat Web")
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    def home() -> RedirectResponse:
        return RedirectResponse(url="/chat", status_code=303)

    @app.get("/chat", response_class=HTMLResponse)
    def chat_page(
        request: Request,
        agent_name: str | None = None,
        model_name: str | None = None,
        session_id: str | None = None,
        flash_message: str | None = None,
    ) -> HTMLResponse:
        current_agent = normalize_agent_name(agent_name)
        current_model = (model_name or default_model_name()).strip() or default_model_name()
        current_session_id = session_id or ""
        messages = []
        error_message = None

        if current_session_id:
            try:
                ensure_session_exists(current_session_id)
                messages = load_session_messages(current_session_id)
            except SessionNotFoundException:
                error_message = "会话不存在，请从左侧重新选择或创建新会话。"
                current_session_id = ""
                messages = []
            except Exception as exc:
                error_message = f"加载会话失败：{exc}"
                current_session_id = ""
                messages = []

        return TEMPLATES.TemplateResponse(
            request,
            "chat.html",
            _build_chat_context(
                request=request,
                current_agent=current_agent,
                current_model=current_model,
                current_session_id=current_session_id,
                messages=messages,
                error_message=error_message,
                flash_message=flash_message,
            ),
        )

    @app.post("/chat/session", response_class=HTMLResponse)
    def create_session(
        request: Request,
        agent_name: str = Form(...),
        model_name: str = Form(...),
    ) -> Response:
        current_agent = normalize_agent_name(agent_name)
        current_model = model_name.strip() or default_model_name()
        try:
            session_id = create_chat_session(current_agent, current_model)
        except Exception as exc:
            return TEMPLATES.TemplateResponse(
                request,
                "chat.html",
                _build_chat_context(
                    request=request,
                    current_agent=current_agent,
                    current_model=current_model,
                    current_session_id="",
                    messages=[],
                    error_message=f"创建会话失败：{exc}",
                    flash_message=None,
                ),
                status_code=400,
            )

        query = urlencode(
            {
                "agent_name": current_agent,
                "model_name": current_model,
                "session_id": session_id,
                "flash_message": "已创建新会话。",
            }
        )
        return RedirectResponse(url=f"/chat?{query}", status_code=303)

    @app.post("/chat/message", response_class=HTMLResponse)
    def send_message(
        request: Request,
        agent_name: str = Form(...),
        model_name: str = Form(...),
        session_id: str = Form(...),
        message: str = Form(...),
    ) -> Response:
        current_agent = normalize_agent_name(agent_name)
        current_model = model_name.strip() or default_model_name()
        current_session_id = session_id.strip()
        user_message = message.strip()

        if not current_session_id:
            return TEMPLATES.TemplateResponse(
                request,
                "chat.html",
                _build_chat_context(
                    request=request,
                    current_agent=current_agent,
                    current_model=current_model,
                    current_session_id="",
                    messages=[],
                    error_message="请先创建或选择一个会话。",
                    flash_message=None,
                ),
                status_code=400,
            )
        if not user_message:
            return TEMPLATES.TemplateResponse(
                request,
                "chat.html",
                _build_chat_context(
                    request=request,
                    current_agent=current_agent,
                    current_model=current_model,
                    current_session_id=current_session_id,
                    messages=load_session_messages(current_session_id) if _session_exists(current_session_id) else [],
                    error_message="请输入消息内容。",
                    flash_message=None,
                ),
                status_code=400,
            )

        try:
            send_chat_message(current_agent, current_model, current_session_id, user_message)
        except SessionNotFoundException:
            return TEMPLATES.TemplateResponse(
                request,
                "chat.html",
                _build_chat_context(
                    request=request,
                    current_agent=current_agent,
                    current_model=current_model,
                    current_session_id="",
                    messages=[],
                    error_message="会话不存在，请重新创建或选择会话。",
                    flash_message=None,
                ),
                status_code=400,
            )
        except Exception as exc:
            return TEMPLATES.TemplateResponse(
                request,
                "chat.html",
                _build_chat_context(
                    request=request,
                    current_agent=current_agent,
                    current_model=current_model,
                    current_session_id=current_session_id,
                    messages=load_session_messages(current_session_id) if _session_exists(current_session_id) else [],
                    error_message=f"发送消息失败：{exc}",
                    flash_message=None,
                ),
                status_code=400,
            )

        query = urlencode(
            {
                "agent_name": current_agent,
                "model_name": current_model,
                "session_id": current_session_id,
                "flash_message": "消息已发送。",
            }
        )
        return RedirectResponse(url=f"/chat?{query}", status_code=303)

    for page in ("chains", "tools", "memory", "mcp", "skills"):
        _register_placeholder_route(app, page)

    return app


def _build_chat_context(
    *,
    request: Request,
    current_agent: AgentName,
    current_model: str,
    current_session_id: str,
    messages,
    error_message: str | None,
    flash_message: str | None,
) -> dict:
    return {
        "request": request,
        "page_title": "聊天",
        "nav_items": get_nav_items(),
        "current_page": "chat",
        "agent_options": get_agent_options(),
        "current_agent": current_agent,
        "current_model": current_model,
        "current_session_id": current_session_id,
        "sessions": list_recent_sessions(),
        "messages": messages,
        "error_message": error_message,
        "flash_message": flash_message,
    }


def _register_placeholder_route(app: FastAPI, page_key: str) -> None:
    title, description = placeholder_copy(page_key)

    @app.get(f"/{page_key}", response_class=HTMLResponse, name=f"{page_key}_page")
    def placeholder_page(request: Request, _page_key: str = page_key, _title: str = title, _description: str = description) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request,
            "placeholder.html",
            {
                "request": request,
                "page_title": _title,
                "nav_items": get_nav_items(),
                "current_page": _page_key,
                "placeholder_title": _title,
                "placeholder_description": _description,
            },
        )


def _session_exists(session_id: str) -> bool:
    try:
        ensure_session_exists(session_id)
    except Exception:
        return False
    return True
