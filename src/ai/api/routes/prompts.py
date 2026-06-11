"""提示词模板路由 — CRUD、渲染、版本管理。"""

from __future__ import annotations

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query

from src.ai.api.schemas.common import MessageResponse
from src.ai.api.schemas.prompts import (
    PromptDataResponse,
    PromptRenderRequestSchema,
    PromptRenderResultResponse,
    PromptRollbackRequest,
    PromptSaveRequest,
    PromptUpdateRequest,
    PromptVersionResponse,
)
from src.ai.core.container import AppContainer
from src.ai.service.prompt_service import PromptApiService

router = APIRouter()


@router.get("", response_model=list[PromptDataResponse], summary="列出模板")
@inject
async def list_templates(
    svc: Annotated[
        PromptApiService,
        Depends(Provide[AppContainer.service_container.prompt_api_service]),
    ],
    category: str | None = Query(default=None, description="按分类过滤"),
) -> list[PromptDataResponse]:
    """列出所有提示词模板。"""
    templates = svc.list_templates(category=category)
    return [PromptDataResponse(**t) for t in templates]


@router.post("", response_model=PromptDataResponse, summary="创建模板")
@inject
async def save_template(
    req: PromptSaveRequest,
    svc: Annotated[
        PromptApiService,
        Depends(Provide[AppContainer.service_container.prompt_api_service]),
    ],
) -> PromptDataResponse:
    """创建或保存提示词模板。"""
    data = svc.save_template(
        prompt_key=req.prompt_key,
        template=req.template,
        display_name=req.display_name,
        description=req.description,
        category=req.category,
        change_note=req.change_note,
    )
    return PromptDataResponse(**data)


@router.get("/{prompt_key}", response_model=PromptDataResponse, summary="获取模板")
@inject
async def get_template(
    prompt_key: str,
    svc: Annotated[
        PromptApiService,
        Depends(Provide[AppContainer.service_container.prompt_api_service]),
    ],
) -> PromptDataResponse:
    """获取指定提示词模板。"""
    try:
        data = svc.get_template(prompt_key)
        return PromptDataResponse(**data)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"模板不存在: {prompt_key}")


@router.put("/{prompt_key}", response_model=PromptDataResponse, summary="更新模板")
@inject
async def update_template(
    prompt_key: str,
    req: PromptUpdateRequest,
    svc: Annotated[
        PromptApiService,
        Depends(Provide[AppContainer.service_container.prompt_api_service]),
    ],
) -> PromptDataResponse:
    """更新提示词模板元数据。"""
    try:
        data = svc.update_template(
            prompt_key,
            display_name=req.display_name,
            description=req.description,
            category=req.category,
            enabled=req.enabled,
        )
        return PromptDataResponse(**data)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"模板不存在: {prompt_key}")


@router.delete("/{prompt_key}", response_model=MessageResponse, summary="删除模板")
@inject
async def delete_template(
    prompt_key: str,
    svc: Annotated[
        PromptApiService,
        Depends(Provide[AppContainer.service_container.prompt_api_service]),
    ],
) -> MessageResponse:
    """删除提示词模板。"""
    try:
        svc.delete_template(prompt_key)
        return MessageResponse(message=f"已删除: {prompt_key}")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"模板不存在: {prompt_key}")


@router.post("/render", response_model=PromptRenderResultResponse, summary="渲染模板")
@inject
async def render_template(
    req: PromptRenderRequestSchema,
    svc: Annotated[
        PromptApiService,
        Depends(Provide[AppContainer.service_container.prompt_api_service]),
    ],
) -> PromptRenderResultResponse:
    """渲染提示词模板。"""
    result = svc.render(prompt_key=req.prompt_key, variables=req.variables)
    return PromptRenderResultResponse(**result)


@router.get(
    "/{prompt_key}/versions",
    response_model=list[PromptVersionResponse],
    summary="列出版本",
)
@inject
async def list_versions(
    prompt_key: str,
    svc: Annotated[
        PromptApiService,
        Depends(Provide[AppContainer.service_container.prompt_api_service]),
    ],
) -> list[PromptVersionResponse]:
    """列出模板的版本历史。"""
    versions = svc.list_versions(prompt_key)
    return [PromptVersionResponse(**v) for v in versions]


@router.get(
    "/{prompt_key}/versions/{version}",
    response_model=PromptVersionResponse,
    summary="获取版本",
)
@inject
async def get_version(
    prompt_key: str,
    version: int,
    svc: Annotated[
        PromptApiService,
        Depends(Provide[AppContainer.service_container.prompt_api_service]),
    ],
) -> PromptVersionResponse:
    """获取指定版本。"""
    data = svc.get_version(prompt_key, version)
    return PromptVersionResponse(**data)


@router.post(
    "/{prompt_key}/rollback", response_model=PromptDataResponse, summary="回滚版本"
)
@inject
async def rollback_template(
    prompt_key: str,
    req: PromptRollbackRequest,
    svc: Annotated[
        PromptApiService,
        Depends(Provide[AppContainer.service_container.prompt_api_service]),
    ],
) -> PromptDataResponse:
    """回滚模板到指定版本。"""
    data = svc.rollback_template(
        prompt_key, version=req.version, change_note=req.change_note
    )
    return PromptDataResponse(**data)
