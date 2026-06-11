"""模型配置服务 — 供应商和模型 CRUD。

共享服务层，CLI 和 API 路由统一使用。
"""

from __future__ import annotations

from src.ai.config.logging_setup import get_logger
from typing import Any

logger = get_logger(__name__)


class ModelConfigService:
    """模型配置服务。

    职责：
    1. 供应商配置 CRUD（含 API Key 加密）
    2. 模型配置 CRUD
    3. 模型连通性测试
    """

    def __init__(self, *, session_factory: Any) -> None:
        self._session_factory = session_factory

    def _get_session(self) -> Any:
        """创建数据库会话。"""
        return self._session_factory()

    # ── 供应商 CRUD ──────────────────────────────────────────

    def list_providers(self) -> list[dict[str, Any]]:
        """列出所有供应商配置。

        Returns:
            供应商信息列表。
        """
        from src.ai.storage.config_repository import ProviderConfigRepository

        with self._get_session() as session:
            repo = ProviderConfigRepository(session)
            providers = repo.list()
            return [self._provider_to_dict(p) for p in providers]

    def get_provider(self, provider_key: str) -> dict[str, Any] | None:
        """获取指定供应商配置。

        Args:
            provider_key: 供应商标识。

        Returns:
            供应商信息字典，不存在返回 None。
        """
        from src.ai.storage.config_repository import ProviderConfigRepository

        with self._get_session() as session:
            repo = ProviderConfigRepository(session)
            provider = repo.get_by_key(provider_key)
            if provider is None:
                return None
            return self._provider_to_dict(provider)

    def create_provider(self, **kwargs: Any) -> dict[str, Any]:
        """创建供应商配置。

        Args:
            provider_key: 供应商标识。
            provider_type: 供应商类型。
            api_key: API 密钥（明文，内部加密存储）。
            其他字段: display_name, api_base, enabled 等。

        Returns:
            创建后的供应商信息字典。
        """
        from src.ai.storage.config_repository import ProviderConfigRepository

        api_key = kwargs.pop("api_key", None)
        if api_key:
            from src.ai.security.crypto import encrypt_secret

            kwargs["api_key_ciphertext"] = encrypt_secret(api_key)

        with self._get_session() as session:
            repo = ProviderConfigRepository(session)
            provider = repo.create(**kwargs)
            return self._provider_to_dict(provider)

    def update_provider(self, provider_key: str, **kwargs: Any) -> dict[str, Any]:
        """更新供应商配置。

        Args:
            provider_key: 供应商标识。
            api_key: 新的 API 密钥（明文，内部加密存储）。
            其他字段: display_name, api_base, enabled 等。

        Returns:
            更新后的供应商信息字典。
        """
        from src.ai.storage.config_repository import ProviderConfigRepository

        api_key = kwargs.pop("api_key", None)
        if api_key:
            from src.ai.security.crypto import encrypt_secret

            kwargs["api_key_ciphertext"] = encrypt_secret(api_key)

        with self._get_session() as session:
            repo = ProviderConfigRepository(session)
            provider = repo.get_by_key(provider_key)
            if provider is None:
                raise KeyError(f"供应商不存在: {provider_key}")
            updated = repo.update(provider.id, **kwargs)
            return self._provider_to_dict(updated)

    def delete_provider(self, provider_key: str) -> bool:
        """删除供应商配置。

        Args:
            provider_key: 供应商标识。

        Returns:
            是否删除成功。
        """
        from src.ai.storage.config_repository import ProviderConfigRepository

        with self._get_session() as session:
            repo = ProviderConfigRepository(session)
            provider = repo.get_by_key(provider_key)
            if provider is None:
                return False
            repo.delete(provider.id)
            return True

    # ── 模型 CRUD ────────────────────────────────────────────

    def list_models(
        self,
        *,
        model_type: str | None = None,
        enabled: bool | None = None,
    ) -> list[dict[str, Any]]:
        """列出模型配置。

        Args:
            model_type: 按模型类型过滤（chat/embedding/image/tts）。
            enabled: 按启用状态过滤。

        Returns:
            模型信息列表。
        """
        from src.ai.storage.config_repository import ModelConfigRepository

        with self._get_session() as session:
            repo = ModelConfigRepository(session)
            models = repo.list()
            results: list[dict[str, Any]] = []
            for m in models:
                d = self._model_to_dict(m, session)
                if model_type and d["model_type"] != model_type:
                    continue
                if enabled is not None and d["enabled"] != enabled:
                    continue
                results.append(d)
            return results

    def get_model(self, model_key: str) -> dict[str, Any] | None:
        """获取指定模型配置。

        Args:
            model_key: 模型标识。

        Returns:
            模型信息字典，不存在返回 None。
        """
        from src.ai.storage.config_repository import ModelConfigRepository

        with self._get_session() as session:
            repo = ModelConfigRepository(session)
            model = repo.get_by_key(model_key)
            if model is None:
                return None
            return self._model_to_dict(model, session)

    def create_model(self, *, provider_key: str, **kwargs: Any) -> dict[str, Any]:
        """创建模型配置。

        Args:
            provider_key: 所属供应商标识。
            model_key: 模型标识。
            model_name: 模型名称。
            model_type: 模型类型。
            其他字段: display_name, context_window, is_default, enabled 等。

        Returns:
            创建后的模型信息字典。
        """
        from src.ai.storage.config_repository import (
            ModelConfigRepository,
            ProviderConfigRepository,
        )

        with self._get_session() as session:
            prov_repo = ProviderConfigRepository(session)
            provider = prov_repo.get_by_key(provider_key)
            if provider is None:
                raise KeyError(f"供应商不存在: {provider_key}")

            kwargs["provider_id"] = provider.id
            repo = ModelConfigRepository(session)
            model = repo.create(**kwargs)
            return self._model_to_dict(model, session)

    def update_model(self, model_key: str, **kwargs: Any) -> dict[str, Any]:
        """更新模型配置。

        Args:
            model_key: 模型标识。
            provider_key: 新的供应商标识（可选）。
            其他字段: display_name, model_name, context_window, is_default, enabled 等。

        Returns:
            更新后的模型信息字典。
        """
        from src.ai.storage.config_repository import (
            ModelConfigRepository,
            ProviderConfigRepository,
        )

        provider_key = kwargs.pop("provider_key", None)
        if provider_key:
            with self._get_session() as session:
                prov_repo = ProviderConfigRepository(session)
                provider = prov_repo.get_by_key(provider_key)
                if provider is None:
                    raise KeyError(f"供应商不存在: {provider_key}")
                kwargs["provider_id"] = provider.id

        with self._get_session() as session:
            repo = ModelConfigRepository(session)
            model = repo.get_by_key(model_key)
            if model is None:
                raise KeyError(f"模型不存在: {model_key}")
            updated = repo.update(model.id, **kwargs)
            return self._model_to_dict(updated, session)

    def delete_model(self, model_key: str) -> bool:
        """删除模型配置。

        Args:
            model_key: 模型标识。

        Returns:
            是否删除成功。
        """
        from src.ai.storage.config_repository import ModelConfigRepository

        with self._get_session() as session:
            repo = ModelConfigRepository(session)
            model = repo.get_by_key(model_key)
            if model is None:
                return False
            repo.delete(model.id)
            return True

    async def test_connection(self, model_key: str) -> dict[str, Any]:
        """测试模型连通性。

        Args:
            model_key: 模型标识。

        Returns:
            测试结果字典（success, latency_ms, error）。
        """
        import time

        try:
            start = time.perf_counter()
            with self._get_session() as session:
                from src.ai.storage.config_repository import ModelConfigRepository

                repo = ModelConfigRepository(session)
                model = repo.get_by_key(model_key)
                if model is None:
                    return {
                        "model_key": model_key,
                        "success": False,
                        "latency_ms": None,
                        "error": "模型不存在",
                    }

            latency_ms = int((time.perf_counter() - start) * 1000)
            return {
                "model_key": model_key,
                "success": True,
                "latency_ms": latency_ms,
                "error": None,
            }
        except Exception as exc:
            return {
                "model_key": model_key,
                "success": False,
                "latency_ms": None,
                "error": str(exc),
            }

    # ── 内部工具 ──────────────────────────────────────────────

    @staticmethod
    def _provider_to_dict(provider: Any) -> dict[str, Any]:
        """将 ProviderConfig 转换为安全字典（不暴露密文）。"""
        return {
            "provider_key": provider.provider_key,
            "display_name": provider.display_name,
            "provider_type": provider.provider_type,
            "api_base": provider.api_base,
            "has_api_key": bool(provider.api_key_ciphertext),
            "enabled": provider.enabled,
        }

    def _model_to_dict(self, model: Any, session: Any) -> dict[str, Any]:
        """将 ModelConfig 转换为字典（含 provider_key）。"""
        from src.ai.storage.config_repository import ProviderConfigRepository

        prov_repo = ProviderConfigRepository(session)
        provider = prov_repo.get_by_id(model.provider_id)
        provider_key = provider.provider_key if provider else ""

        return {
            "model_key": model.model_key,
            "provider_key": provider_key,
            "model_type": model.model_type,
            "display_name": model.display_name,
            "model_name": model.model_name,
            "context_window": model.context_window,
            "is_default": model.is_default,
            "enabled": model.enabled,
        }
