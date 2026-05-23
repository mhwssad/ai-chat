"""供应商路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from src.ai.api.dependencies import db_session
from src.ai.api.schemas.models import (
    ProviderCreateRequest,
    ProviderResponse,
    ProviderUpdateRequest,
)
from src.ai.api.services.model_service import ModelService

router = APIRouter()


@router.get("", response_model=list[ProviderResponse])
async def list_providers(session: Session = Depends(db_session)):
    providers = ModelService(session).list_all_providers()
    return [
        ProviderResponse(
            id=p.id,
            provider_key=p.provider_key,
            display_name=p.display_name,
            base_url=p.base_url,
            default_model_id=p.default_model_id,
            enabled=p.enabled,
            status=p.status,
            has_api_key=bool(p.api_key_encrypted),
        )
        for p in providers
    ]


@router.post("", response_model=ProviderResponse, status_code=201)
async def create_provider(payload: ProviderCreateRequest, session: Session = Depends(db_session)):
    p = ModelService(session).create_provider(payload)
    return ProviderResponse(
        id=p.id,
        provider_key=p.provider_key,
        display_name=p.display_name,
        base_url=p.base_url,
        default_model_id=p.default_model_id,
        enabled=p.enabled,
        status=p.status,
        has_api_key=bool(p.api_key_encrypted),
    )


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(provider_id: int, session: Session = Depends(db_session)):
    p = ModelService(session).get_provider(provider_id)
    return ProviderResponse(
        id=p.id,
        provider_key=p.provider_key,
        display_name=p.display_name,
        base_url=p.base_url,
        default_model_id=p.default_model_id,
        enabled=p.enabled,
        status=p.status,
        has_api_key=bool(p.api_key_encrypted),
    )


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: int, payload: ProviderUpdateRequest, session: Session = Depends(db_session)
):
    p = ModelService(session).update_provider(provider_id, payload)
    return ProviderResponse(
        id=p.id,
        provider_key=p.provider_key,
        display_name=p.display_name,
        base_url=p.base_url,
        default_model_id=p.default_model_id,
        enabled=p.enabled,
        status=p.status,
        has_api_key=bool(p.api_key_encrypted),
    )


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(provider_id: int, session: Session = Depends(db_session)):
    ModelService(session).delete_provider(provider_id)
