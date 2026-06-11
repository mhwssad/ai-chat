"""模型配置路由 — 供应商/模型 CRUD、测试连通性。"""

from __future__ import annotations

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query

from src.ai.api.schemas.common import MessageResponse
from src.ai.api.schemas.models import (
    ModelConfigCreateRequest,
    ModelConfigResponse,
    ModelConfigUpdateRequest,
    ModelTestResponse,
    ProviderConfigCreateRequest,
    ProviderConfigResponse,
    ProviderConfigUpdateRequest,
)
from src.ai.core.container import AppContainer
from src.ai.service.model_config_service import ModelConfigService

router = APIRouter()


# ── 供应商 ────────────────────────────────────────────────────


@router.get(
    "/providers", response_model=list[ProviderConfigResponse], summary="列出供应商"
)
@inject
async def list_providers(
    svc: Annotated[
        ModelConfigService,
        Depends(Provide[AppContainer.service_container.model_config_service]),
    ],
) -> list[ProviderConfigResponse]:
    """列出所有供应商配置。"""
    providers = svc.list_providers()
    return [ProviderConfigResponse(**p) for p in providers]


@router.post("/providers", response_model=ProviderConfigResponse, summary="创建供应商")
@inject
async def create_provider(
    req: ProviderConfigCreateRequest,
    svc: Annotated[
        ModelConfigService,
        Depends(Provide[AppContainer.service_container.model_config_service]),
    ],
) -> ProviderConfigResponse:
    """创建供应商配置。"""
    data = svc.create_provider(**req.model_dump())
    return ProviderConfigResponse(**data)


@router.put(
    "/providers/{provider_key}",
    response_model=ProviderConfigResponse,
    summary="更新供应商",
)
@inject
async def update_provider(
    provider_key: str,
    req: ProviderConfigUpdateRequest,
    svc: Annotated[
        ModelConfigService,
        Depends(Provide[AppContainer.service_container.model_config_service]),
    ],
) -> ProviderConfigResponse:
    """更新供应商配置。"""
    try:
        data = svc.update_provider(provider_key, **req.model_dump(exclude_none=True))
        return ProviderConfigResponse(**data)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"供应商不存在: {provider_key}")


@router.delete(
    "/providers/{provider_key}", response_model=MessageResponse, summary="删除供应商"
)
@inject
async def delete_provider(
    provider_key: str,
    svc: Annotated[
        ModelConfigService,
        Depends(Provide[AppContainer.service_container.model_config_service]),
    ],
) -> MessageResponse:
    """删除供应商配置。"""
    deleted = svc.delete_provider(provider_key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"供应商不存在: {provider_key}")
    return MessageResponse(message=f"已删除: {provider_key}")


# ── 模型 ──────────────────────────────────────────────────────


@router.get("", response_model=list[ModelConfigResponse], summary="列出模型")
@inject
async def list_models(
    svc: Annotated[
        ModelConfigService,
        Depends(Provide[AppContainer.service_container.model_config_service]),
    ],
    model_type: str | None = Query(default=None, description="按类型过滤"),
    enabled: bool | None = Query(default=None, description="按启用状态过滤"),
) -> list[ModelConfigResponse]:
    """列出模型配置。"""
    models = svc.list_models(model_type=model_type, enabled=enabled)
    return [ModelConfigResponse(**m) for m in models]


@router.post("", response_model=ModelConfigResponse, summary="创建模型")
@inject
async def create_model(
    req: ModelConfigCreateRequest,
    svc: Annotated[
        ModelConfigService,
        Depends(Provide[AppContainer.service_container.model_config_service]),
    ],
) -> ModelConfigResponse:
    """创建模型配置。"""
    data = svc.create_model(
        provider_key=req.provider_key,
        model_key=req.model_key,
        model_type=req.model_type,
        display_name=req.display_name,
        model_name=req.model_name,
        context_window=req.context_window,
        is_default=req.is_default,
        enabled=req.enabled,
    )
    return ModelConfigResponse(**data)


@router.put("/{model_key}", response_model=ModelConfigResponse, summary="更新模型")
@inject
async def update_model(
    model_key: str,
    req: ModelConfigUpdateRequest,
    svc: Annotated[
        ModelConfigService,
        Depends(Provide[AppContainer.service_container.model_config_service]),
    ],
) -> ModelConfigResponse:
    """更新模型配置。"""
    try:
        data = svc.update_model(model_key, **req.model_dump(exclude_none=True))
        return ModelConfigResponse(**data)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"模型不存在: {model_key}")


@router.delete("/{model_key}", response_model=MessageResponse, summary="删除模型")
@inject
async def delete_model(
    model_key: str,
    svc: Annotated[
        ModelConfigService,
        Depends(Provide[AppContainer.service_container.model_config_service]),
    ],
) -> MessageResponse:
    """删除模型配置。"""
    deleted = svc.delete_model(model_key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"模型不存在: {model_key}")
    return MessageResponse(message=f"已删除: {model_key}")


@router.post(
    "/{model_key}/test", response_model=ModelTestResponse, summary="测试连通性"
)
@inject
async def test_connection(
    model_key: str,
    svc: Annotated[
        ModelConfigService,
        Depends(Provide[AppContainer.service_container.model_config_service]),
    ],
) -> ModelTestResponse:
    """测试模型连通性。"""
    result = await svc.test_connection(model_key)
    return ModelTestResponse(**result)
