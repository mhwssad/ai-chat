"""模型和供应商服务。"""

from __future__ import annotations

from sqlmodel import Session

from src.ai.api.schemas.models import (
    ModelCreateRequest,
    ModelUpdateRequest,
    ProviderCreateRequest,
    ProviderUpdateRequest,
)
from src.ai.exception.base_exception import BaseExceptions
from src.ai.storage import ModelRepository, ProviderRepository


class ModelService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._provider_repo = ProviderRepository(session)
        self._model_repo = ModelRepository(session)

    # ── Provider 查询 ──────────────────────────────────────

    def list_providers(self) -> list:
        return self._provider_repo.get_enabled()

    def list_all_providers(self) -> list:
        return self._provider_repo.list(order_by="provider_key", descending=False)

    def get_provider(self, provider_id: int):
        provider = self._provider_repo.get_by_id(provider_id)
        if not provider:
            raise BaseExceptions("供应商不存在", error_code="PROVIDER_NOT_FOUND")
        return provider

    # ── Provider CRUD ──────────────────────────────────────

    def create_provider(self, payload: ProviderCreateRequest):
        return self._provider_repo.create_with_api_key(
            api_key=payload.api_key,
            provider_key=payload.provider_key,
            display_name=payload.display_name,
            base_url=payload.base_url,
            enabled=payload.enabled,
        )

    def update_provider(self, provider_id: int, payload: ProviderUpdateRequest):
        provider = self.get_provider(provider_id)
        updates = payload.model_dump(exclude_unset=True, exclude={"api_key"})
        if updates:
            self._provider_repo.update(provider, **updates)
        if "api_key" in payload.model_dump(exclude_unset=True):
            self._provider_repo.update_api_key(provider, payload.api_key)
        return provider

    def delete_provider(self, provider_id: int) -> bool:
        self.get_provider(provider_id)
        models = self._model_repo.get_by_provider(provider_id)
        if models:
            raise BaseExceptions(
                f"供应商下还有 {len(models)} 个模型，请先删除",
                error_code="PROVIDER_HAS_MODELS",
            )
        return self._provider_repo.delete_by_id(provider_id)

    # ── Model 查询 ─────────────────────────────────────────

    def list_models(self) -> list:
        return self._model_repo.get_enabled()

    def list_all_models(self) -> list:
        return self._model_repo.list(order_by="model_key", descending=False)

    def get_model(self, model_id: int):
        model = self._model_repo.get_by_id(model_id)
        if not model:
            raise BaseExceptions("模型不存在", error_code="MODEL_NOT_FOUND")
        return model

    # ── Model CRUD ─────────────────────────────────────────

    def create_model(self, payload: ModelCreateRequest):
        return self._model_repo.create(**payload.model_dump())

    def update_model(self, model_id: int, payload: ModelUpdateRequest):
        model = self.get_model(model_id)
        updates = payload.model_dump(exclude_unset=True, exclude_none=True)
        if updates:
            self._model_repo.update(model, **updates)
        return model

    def delete_model(self, model_id: int) -> bool:
        self.get_model(model_id)
        return self._model_repo.delete_by_id(model_id)
