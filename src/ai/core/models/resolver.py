"""数据库模型配置解析。"""

from __future__ import annotations

from typing import Any

from src.ai.exception.llm_exception import LLMException
from src.ai.storage import Model, ModelRepository, Provider, ProviderRepository

from .types import ModelRequest


class ModelResolver:
    """从数据库解析 Provider 和 Model。"""

    def resolve(self, session: Any, request: ModelRequest) -> tuple[Provider, Model]:
        model_repo = ModelRepository(session)
        provider_repo = ProviderRepository(session)

        model: Model | None = None
        provider: Provider | None = None

        if request.model_id is not None:
            model = model_repo.get_by_id(request.model_id)
            if model is None:
                raise LLMException("模型不存在", context={"model_id": request.model_id})
            provider = provider_repo.get_by_id(model.provider_id)
        elif request.provider_key and request.model_key:
            provider = provider_repo.get_by_key(request.provider_key)
            if provider is not None and provider.id is not None:
                model = model_repo.get_by_key(provider.id, request.model_key)
        else:
            providers = provider_repo.get_enabled()
            for candidate in providers:
                if candidate.default_model_id is not None:
                    model = model_repo.get_by_id(candidate.default_model_id)
                    provider = candidate
                    break

        if provider is None:
            raise LLMException("供应商不存在或未启用", context={"provider_key": request.provider_key})
        if model is None:
            raise LLMException(
                "模型不存在或未配置",
                context={"provider_key": provider.provider_key, "model_key": request.model_key},
            )
        if not provider.enabled:
            raise LLMException("供应商未启用", context={"provider": provider.provider_key})
        if not model.enabled:
            raise LLMException("模型未启用", context={"model": model.model_key})

        return provider, model
