"""模型路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from src.ai.api.dependencies import db_session
from src.ai.api.schemas.models import (
    ModelCreateRequest,
    ModelResponse,
    ModelUpdateRequest,
)
from src.ai.api.services.model_service import ModelService

router = APIRouter()


def _to_response(m) -> ModelResponse:
    return ModelResponse(
        id=m.id,
        provider_id=m.provider_id,
        model_key=m.model_key,
        display_name=m.display_name,
        model_type=m.model_type,
        request_type=m.request_type,
        enabled=m.enabled,
        supports_streaming=m.supports_streaming,
        supports_tools=m.supports_tools,
        context_window=m.context_window,
        max_output_tokens=m.max_output_tokens,
        currency=m.currency,
    )


@router.get("", response_model=list[ModelResponse])
async def list_models(
    enabled_only: bool = Query(default=True),
    session: Session = Depends(db_session),
):
    svc = ModelService(session)
    models = svc.list_models() if enabled_only else svc.list_all_models()
    return [_to_response(m) for m in models]


@router.post("", response_model=ModelResponse, status_code=201)
async def create_model(payload: ModelCreateRequest, session: Session = Depends(db_session)):
    m = ModelService(session).create_model(payload)
    return _to_response(m)


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: int, session: Session = Depends(db_session)):
    m = ModelService(session).get_model(model_id)
    return _to_response(m)


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: int, payload: ModelUpdateRequest, session: Session = Depends(db_session)
):
    m = ModelService(session).update_model(model_id, payload)
    return _to_response(m)


@router.delete("/{model_id}", status_code=204)
async def delete_model(model_id: int, session: Session = Depends(db_session)):
    ModelService(session).delete_model(model_id)
