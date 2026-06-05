"""配置类数据仓库。"""

from __future__ import annotations

from src.ai.storage.base_repository import BaseRepository
from src.ai.storage.config_models import (
    AppSetting,
    MCPServerRecord,
    ModelConfig,
    ProviderConfig,
    SecurityPolicy,
    SkillConfig,
)


class ProviderConfigRepository(BaseRepository[ProviderConfig]):
    """供应商配置仓库。"""

    model = ProviderConfig

    def get_by_key(self, provider_key: str) -> ProviderConfig | None:
        return self.get_by_field("provider_key", provider_key)

    def list_enabled(self) -> list[ProviderConfig]:
        return self.list(enabled=True, order_by="provider_key", descending=False)


class ModelConfigRepository(BaseRepository[ModelConfig]):
    """模型配置仓库。"""

    model = ModelConfig

    def get_by_key(self, model_key: str) -> ModelConfig | None:
        return self.get_by_field("model_key", model_key)

    def list_enabled(self, *, model_type: str | None = None) -> list[ModelConfig]:
        filters: dict[str, object] = {"enabled": True}
        if model_type is not None:
            filters["model_type"] = model_type
        return self.list(order_by="model_key", descending=False, **filters)

    def get_default(self, model_type: str) -> ModelConfig | None:
        return self.get_by_field("model_type", model_type)


class AppSettingRepository(BaseRepository[AppSetting]):
    """应用设置仓库。"""

    model = AppSetting

    def get_by_key(self, setting_key: str) -> AppSetting | None:
        return self.get_by_field("setting_key", setting_key)

    def list_enabled(self) -> list[AppSetting]:
        return self.list(enabled=True, order_by="setting_key", descending=False)


class MCPServerRepository(BaseRepository[MCPServerRecord]):
    """MCP 配置仓库。"""

    model = MCPServerRecord

    def get_by_key(self, server_key: str) -> MCPServerRecord | None:
        return self.get_by_field("server_key", server_key)

    def list_enabled(self) -> list[MCPServerRecord]:
        return self.list(enabled=True, order_by="server_key", descending=False)


class SkillConfigRepository(BaseRepository[SkillConfig]):
    """技能配置仓库。"""

    model = SkillConfig

    def get_by_key(self, skill_key: str) -> SkillConfig | None:
        return self.get_by_field("skill_key", skill_key)

    def list_enabled(self) -> list[SkillConfig]:
        return self.list(enabled=True, order_by="skill_key", descending=False)


class SecurityPolicyRepository(BaseRepository[SecurityPolicy]):
    """安全策略仓库。"""

    model = SecurityPolicy

    def get_by_key(self, policy_key: str) -> SecurityPolicy | None:
        return self.get_by_field("policy_key", policy_key)

    def list_enabled(self) -> list[SecurityPolicy]:
        return self.list(enabled=True, order_by="policy_key", descending=False)
