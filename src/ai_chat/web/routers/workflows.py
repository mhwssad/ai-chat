"""工作流路由。"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from src.ai_chat.web.deps import TEMPLATES
from src.ai_chat.web.services import (
    create_workflow_from_form,
    delete_workflow_by_name,
    get_nav_items,
    invoke_workflow_by_name,
    list_saved_workflows,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("", response_class=HTMLResponse, name="workflows_page")
def workflows_page(
    request: Request,
    flash_message: str | None = None,
    error_message: str | None = None,
) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(
        request,
        "workflows.html",
        {
            "request": request,
            "page_title": "工作流",
            "nav_items": get_nav_items(),
            "current_page": "workflows",
            "workflows": list_saved_workflows(),
            "flash_message": flash_message,
            "error_message": error_message,
            "invoke_result": None,
            "invoke_workflow_name": None,
        },
    )


@router.post("/create", response_class=HTMLResponse)
def create_workflow(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    model_name: str = Form(""),
    nodes_json: str = Form("[]"),
    edges_json: str = Form("[]"),
    tags: str = Form(""),
) -> Response:
    wf_name = name.strip()
    if not wf_name:
        return TEMPLATES.TemplateResponse(
            request,
            "workflows.html",
            {
                "request": request,
                "page_title": "工作流",
                "nav_items": get_nav_items(),
                "current_page": "workflows",
                "workflows": list_saved_workflows(),
                "flash_message": None,
                "error_message": "工作流名称不能为空。",
                "invoke_result": None,
                "invoke_workflow_name": None,
            },
            status_code=400,
        )
    try:
        create_workflow_from_form(
            name=wf_name,
            description=description.strip(),
            model_name=model_name.strip(),
            nodes_json=nodes_json,
            edges_json=edges_json,
            tags=tags.strip(),
        )
    except Exception as exc:
        return TEMPLATES.TemplateResponse(
            request,
            "workflows.html",
            {
                "request": request,
                "page_title": "工作流",
                "nav_items": get_nav_items(),
                "current_page": "workflows",
                "workflows": list_saved_workflows(),
                "flash_message": None,
                "error_message": f"创建失败：{exc}",
                "invoke_result": None,
                "invoke_workflow_name": None,
            },
            status_code=400,
        )
    return RedirectResponse(url="/workflows?flash_message=工作流创建成功。", status_code=303)


@router.post("/{wf_name}/invoke", response_class=HTMLResponse)
def invoke_workflow(
    request: Request,
    wf_name: str,
    input_text: str = Form(...),
) -> HTMLResponse:
    user_input = input_text.strip()
    result_text = ""
    error = None
    if not user_input:
        error = "请输入内容。"
    else:
        try:
            result_text = invoke_workflow_by_name(wf_name, user_input)
        except Exception as exc:
            error = f"执行失败：{exc}"

    return TEMPLATES.TemplateResponse(
        request,
        "workflows.html",
        {
            "request": request,
            "page_title": "工作流",
            "nav_items": get_nav_items(),
            "current_page": "workflows",
            "workflows": list_saved_workflows(),
            "flash_message": None,
            "error_message": error,
            "invoke_result": result_text,
            "invoke_workflow_name": wf_name,
        },
    )


@router.post("/{wf_name}/delete", response_class=HTMLResponse)
def delete_workflow(request: Request, wf_name: str) -> Response:
    try:
        delete_workflow_by_name(wf_name)
    except Exception as exc:
        return RedirectResponse(
            url=f"/workflows?error_message=删除失败：{exc}",
            status_code=303,
        )
    return RedirectResponse(url="/workflows?flash_message=工作流已删除。", status_code=303)
