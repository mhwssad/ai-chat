"""调用链路由。"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from src.ai_chat.web.deps import TEMPLATES
from src.ai_chat.web.services import (
    create_chain_from_form,
    delete_chain_by_name,
    get_chain_type_options,
    get_nav_items,
    invoke_chain_by_name,
    list_saved_chains,
)

router = APIRouter(prefix="/chains", tags=["chains"])


@router.get("", response_class=HTMLResponse, name="chains_page")
def chains_page(
    request: Request,
    flash_message: str | None = None,
    error_message: str | None = None,
) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(
        request,
        "chains.html",
        {
            "request": request,
            "page_title": "调用链",
            "page_subtitle": "创建和管理 LCEL 调用链配置。",
            "nav_items": get_nav_items(),
            "current_page": "chains",
            "chain_types": get_chain_type_options(),
            "chains": list_saved_chains(),
            "flash_message": flash_message,
            "error_message": error_message,
            "invoke_result": None,
            "invoke_chain_name": None,
        },
    )


@router.post("/create", response_class=HTMLResponse)
def create_chain(
    request: Request,
    name: str = Form(...),
    chain_type: str = Form(...),
    model_name: str = Form(""),
    description: str = Form(""),
    tags: str = Form(""),
) -> Response:
    chain_name = name.strip()
    if not chain_name:
        return TEMPLATES.TemplateResponse(
            request,
            "chains.html",
            {
                "request": request,
                "page_title": "调用链",
            "page_subtitle": "创建和管理 LCEL 调用链配置。",
                "nav_items": get_nav_items(),
                "current_page": "chains",
                "chain_types": get_chain_type_options(),
                "chains": list_saved_chains(),
                "flash_message": None,
                "error_message": "链名称不能为空。",
                "invoke_result": None,
                "invoke_chain_name": None,
            },
            status_code=400,
        )
    try:
        create_chain_from_form(
            name=chain_name,
            chain_type=chain_type,
            model_name=model_name.strip(),
            description=description.strip(),
            tags=tags.strip(),
        )
    except Exception as exc:
        return TEMPLATES.TemplateResponse(
            request,
            "chains.html",
            {
                "request": request,
                "page_title": "调用链",
            "page_subtitle": "创建和管理 LCEL 调用链配置。",
                "nav_items": get_nav_items(),
                "current_page": "chains",
                "chain_types": get_chain_type_options(),
                "chains": list_saved_chains(),
                "flash_message": None,
                "error_message": f"创建失败：{exc}",
                "invoke_result": None,
                "invoke_chain_name": None,
            },
            status_code=400,
        )
    return RedirectResponse(url="/chains?flash_message=链创建成功。", status_code=303)


@router.post("/{chain_name}/invoke", response_class=HTMLResponse)
def invoke_chain(
    request: Request,
    chain_name: str,
    input_text: str = Form(...),
) -> HTMLResponse:
    user_input = input_text.strip()
    result_text = ""
    error = None
    if not user_input:
        error = "请输入内容。"
    else:
        try:
            result_text = invoke_chain_by_name(chain_name, user_input)
        except Exception as exc:
            error = f"执行失败：{exc}"

    return TEMPLATES.TemplateResponse(
        request,
        "chains.html",
        {
            "request": request,
            "page_title": "调用链",
            "page_subtitle": "创建和管理 LCEL 调用链配置。",
            "nav_items": get_nav_items(),
            "current_page": "chains",
            "chain_types": get_chain_type_options(),
            "chains": list_saved_chains(),
            "flash_message": None,
            "error_message": error,
            "invoke_result": result_text,
            "invoke_chain_name": chain_name,
        },
    )


@router.post("/{chain_name}/delete", response_class=HTMLResponse)
def delete_chain(request: Request, chain_name: str) -> Response:
    try:
        delete_chain_by_name(chain_name)
    except Exception as exc:
        return RedirectResponse(
            url=f"/chains?error_message=删除失败：{exc}",
            status_code=303,
        )
    return RedirectResponse(url="/chains?flash_message=链已删除。", status_code=303)
