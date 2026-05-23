"""HTML 页面路由。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from src.ai.api.dependencies import db_session
from src.ai.api.services.model_service import ModelService
from src.ai.api.services.tool_service import ToolService
from src.ai.api.services.usage_service import UsageService

BASE_DIR = Path(__file__).resolve().parent.parent
templates_dir = BASE_DIR / "templates"

templates = Jinja2Templates(directory=templates_dir)
templates.env.filters["format_number"] = lambda v: f"{v:,}"


router = APIRouter()

# ── 导航项 ──────────────────────────────────────────────────

NAV_ITEMS = [
    {"key": "chat", "label": "Chat", "href": "/"},
    {"key": "models", "label": "Models", "href": "/models"},
    {"key": "tools", "label": "Tools", "href": "/tools"},
    {"key": "mcp", "label": "MCP", "href": "/mcp"},
    {"key": "rag", "label": "RAG", "href": "/rag"},
    {"key": "prompts", "label": "Prompts", "href": "/prompts"},
    {"key": "memory", "label": "Memory", "href": "/memory"},
    {"key": "usage", "label": "Usage", "href": "/usage"},
]


def _ctx(request: Request, current_page: str, **kwargs) -> dict:
    """构建模板公共上下文。"""
    return {
        "request": request,
        "current_page": current_page,
        "nav_items": NAV_ITEMS,
        "flash_message": request.query_params.get("msg"),
        "flash_type": request.query_params.get("msg_type", "success"),
        **kwargs,
    }


def _redirect(url: str, msg: str = "", msg_type: str = "success") -> RedirectResponse:
    """带 flash 消息的重定向。"""
    if msg:
        sep = "&" if "?" in url else "?"
        url += f"{sep}msg={msg}&msg_type={msg_type}"
    return RedirectResponse(url, status_code=303)


# ── Chat ────────────────────────────────────────────────────


@router.get("/")
async def chat_page(request: Request, session: Session = Depends(db_session)):
    svc = ModelService(session)
    models = svc.list_models()
    tools = ToolService().list_tools(enabled_only=False)
    return templates.TemplateResponse(
        request,
        "pages/chat.html",
        _ctx(
            request,
            "chat",
            page_title="Chat",
            hide_page_header=True,
            models=models,
            tools=tools,
            selected_model_id=None,
        ),
    )


# ── Models ──────────────────────────────────────────────────


def _model_to_dict(obj) -> dict:
    """将 SQLModel 对象转为可 JSON 序列化的字典。"""
    from datetime import datetime

    def _convert(v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    if hasattr(obj, "model_dump"):
        return {k: _convert(v) for k, v in obj.model_dump().items()}
    return {c.name: _convert(getattr(obj, c.name)) for c in obj.__table__.columns}


@router.get("/models")
async def models_page(request: Request, session: Session = Depends(db_session)):
    svc = ModelService(session)
    providers = [_model_to_dict(p) for p in svc.list_all_providers()]
    models_list = [_model_to_dict(m) for m in svc.list_all_models()]
    return templates.TemplateResponse(
        request,
        "pages/models.html",
        _ctx(
            request,
            "models",
            page_title="Models",
            providers=providers,
            models=models_list,
        ),
    )


@router.post("/models/provider/create")
async def create_provider(request: Request, session: Session = Depends(db_session)):
    from src.ai.api.schemas.models import ProviderCreateRequest

    form = await request.form()
    payload = ProviderCreateRequest(
        provider_key=form.get("provider_key", ""),
        display_name=form.get("display_name") or None,
        base_url=form.get("base_url") or None,
        api_key=form.get("api_key") or None,
        enabled=form.get("enabled") is not None,
    )
    try:
        ModelService(session).create_provider(payload)
        return _redirect("/models", "Provider created")
    except Exception as e:
        return _redirect("/models", str(e), "error")


@router.post("/models/provider/{provider_id}/delete")
async def delete_provider(provider_id: int, session: Session = Depends(db_session)):
    try:
        ModelService(session).delete_provider(provider_id)
        return _redirect("/models", "Provider deleted")
    except Exception as e:
        return _redirect("/models", str(e), "error")


@router.post("/models/create")
async def create_model(request: Request, session: Session = Depends(db_session)):
    from src.ai.api.schemas.models import ModelCreateRequest

    form = await request.form()
    payload = ModelCreateRequest(
        provider_id=int(form.get("provider_id", 0)),
        model_key=form.get("model_key", ""),
        display_name=form.get("display_name") or None,
        model_type=form.get("model_type", "chat"),
        request_type=form.get("request_type", "openai_compatible"),
        supports_streaming=form.get("supports_streaming") is not None,
        supports_tools=form.get("supports_tools") is not None,
        context_window=int(form["context_window"]) if form.get("context_window") else None,
        max_output_tokens=int(form["max_output_tokens"]) if form.get("max_output_tokens") else None,
        input_price=float(form["input_price"]) if form.get("input_price") else None,
        output_price=float(form["output_price"]) if form.get("output_price") else None,
        enabled=form.get("enabled") is not None,
    )
    try:
        ModelService(session).create_model(payload)
        return _redirect("/models", "Model created")
    except Exception as e:
        return _redirect("/models", str(e), "error")


@router.post("/models/{model_id}/delete")
async def delete_model(model_id: int, session: Session = Depends(db_session)):
    try:
        ModelService(session).delete_model(model_id)
        return _redirect("/models", "Model deleted")
    except Exception as e:
        return _redirect("/models", str(e), "error")


# ── Tools ────────────────────────────────────────────────────


@router.get("/tools")
async def tools_page(request: Request):
    tools = ToolService().list_tools(enabled_only=False)
    return templates.TemplateResponse(
        request,
        "pages/tools.html",
        _ctx(request, "tools", page_title="Tools", tools=tools),
    )


# ── MCP ──────────────────────────────────────────────────────


@router.get("/mcp")
async def mcp_page(request: Request):
    from src.ai.api.services.mcp_service import MCPService

    svc = MCPService()
    servers = svc.list_servers()
    try:
        mcp_tools = await svc.list_tools()
    except Exception:
        mcp_tools = []
    return templates.TemplateResponse(
        request,
        "pages/mcp.html",
        _ctx(request, "mcp", page_title="MCP", servers=servers, mcp_tools=mcp_tools),
    )


# ── RAG ──────────────────────────────────────────────────────


@router.get("/rag")
async def rag_page(request: Request):
    from src.ai.rag import rag_service

    documents = rag_service.list_documents() if hasattr(rag_service, "list_documents") else []
    return templates.TemplateResponse(
        request,
        "pages/rag.html",
        _ctx(
            request,
            "rag",
            page_title="RAG",
            documents=documents,
            search_results=None,
        ),
    )


@router.post("/rag/index")
async def rag_index(request: Request):
    from src.ai.api.services.rag_service import RagApiService

    form = await request.form()
    path = form.get("path", "")
    try:
        svc = RagApiService()
        if path.endswith("/") or Path(path).is_dir():
            svc.index_directory(path=path)
        else:
            svc.index_file(path=path)
        return _redirect("/rag", "File indexed")
    except Exception as e:
        return _redirect("/rag", str(e), "error")


@router.post("/rag/search")
async def rag_search(request: Request):
    from src.ai.api.services.rag_service import RagApiService
    from src.ai.rag import rag_service

    form = await request.form()
    query = form.get("query", "")
    try:
        results = RagApiService().search(query, top_k=5)
        results_data = [
            {
                "source_path": r.source_path,
                "title": getattr(r, "title", None),
                "score": r.score,
                "content": r.content,
            }
            for r in results
        ]
    except Exception:
        results_data = []

    documents = rag_service.list_documents() if hasattr(rag_service, "list_documents") else []
    return templates.TemplateResponse(
        request,
        "pages/rag.html",
        _ctx(
            request,
            "rag",
            page_title="RAG",
            documents=documents,
            search_results=results_data,
        ),
    )


# ── Prompts ──────────────────────────────────────────────────


@router.get("/prompts")
async def prompts_page(request: Request, session: Session = Depends(db_session)):
    from src.ai.storage.prompt_repository import PromptTemplateRepository

    repo = PromptTemplateRepository(session)
    prompts = repo.list(order_by="template_key", descending=False) if hasattr(repo, "list") else []
    return templates.TemplateResponse(
        request,
        "pages/prompts.html",
        _ctx(request, "prompts", page_title="Prompts", prompts=prompts),
    )


# ── Memory ───────────────────────────────────────────────────


@router.get("/memory")
async def memory_page(request: Request, session: Session = Depends(db_session)):
    from src.ai.storage.runtime_repository import MemoryEntryRepository

    repo = MemoryEntryRepository(session)
    entries = repo.get_active(limit=50) if hasattr(repo, "get_active") else []
    return templates.TemplateResponse(
        request,
        "pages/memory.html",
        _ctx(
            request,
            "memory",
            page_title="Memory",
            entries=entries,
            search_results=None,
            search_keyword=None,
        ),
    )


@router.post("/memory/search")
async def memory_search(request: Request, session: Session = Depends(db_session)):
    from src.ai.core.memory import memory_service
    from src.ai.storage.runtime_repository import MemoryEntryRepository

    form = await request.form()
    query = form.get("query", "")
    try:
        results = memory_service.find_relevant(query) if hasattr(memory_service, "find_relevant") else []
    except Exception:
        results = []

    repo = MemoryEntryRepository(session)
    entries = repo.get_active(limit=50) if hasattr(repo, "get_active") else []
    return templates.TemplateResponse(
        request,
        "pages/memory.html",
        _ctx(
            request,
            "memory",
            page_title="Memory",
            entries=entries,
            search_results=results,
            search_keyword=query,
        ),
    )


# ── Usage ────────────────────────────────────────────────────


@router.get("/usage")
async def usage_page(
    request: Request,
    session: Session = Depends(db_session),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    svc = UsageService(session)
    summary = svc.get_summary(30)
    by_model = svc.get_summary_by_model(30)
    calls = svc.get_calls(limit=limit, offset=offset)
    return templates.TemplateResponse(
        request,
        "pages/usage.html",
        _ctx(
            request,
            "usage",
            page_title="Usage",
            summary=summary,
            by_model=by_model,
            calls=calls,
            calls_page=calls,
        ),
    )
