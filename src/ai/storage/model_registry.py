"""供应商和模型管理表。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import Column, Index, String, UniqueConstraint
from sqlmodel import Field, SQLModel, select

from src.ai.security.crypto import decrypt_secret, encrypt_secret
from src.ai.storage.base_repository import BaseRepository


def _dt_now() -> datetime:
    return datetime.now()


class Provider(SQLModel, table=True):
    """模型供应商配置。API Key 只允许密文入库。"""

    __tablename__ = "providers"
    __table_args__ = (
        Index("idx_providers_enabled", "enabled"),
        Index("idx_providers_status", "status"),
    )

    id: int | None = Field(default=None, primary_key=True)
    provider_key: str = Field(description="供应商唯一标识", unique=True)
    display_name: str | None = Field(default=None, description="显示名称")
    base_url: str | None = Field(default=None, description="API 基础 URL")
    api_key_encrypted: str | None = Field(default=None, description="加密后的 API Key")
    default_model_id: int | None = Field(default=None, foreign_key="models.id")
    enabled: bool = Field(default=True, description="是否启用")
    status: str = Field(default="unknown", description="健康状态")
    last_checked_at: datetime | None = Field(default=None, description="最近检查时间")
    created_at: datetime = Field(default_factory=_dt_now)
    updated_at: datetime = Field(default_factory=_dt_now)
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )

    def set_api_key(self, api_key: str | None) -> None:
        """加密设置 API Key。"""
        self.api_key_encrypted = encrypt_secret(api_key) if api_key else None

    def get_api_key(self) -> str | None:
        """解密读取 API Key。"""
        if not self.api_key_encrypted:
            return None
        return decrypt_secret(self.api_key_encrypted)

    def get_metadata(self) -> dict[str, Any]:
        if not self.extra:
            return {}
        try:
            return json.loads(self.extra)
        except json.JSONDecodeError:
            return {}

    def set_metadata(self, data: dict[str, Any]) -> None:
        self.extra = json.dumps(data, ensure_ascii=False)


class Model(SQLModel, table=True):
    """可用模型配置。"""

    __tablename__ = "models"
    __table_args__ = (
        UniqueConstraint("provider_id", "model_key", name="uq_provider_model"),
        Index("idx_models_provider_enabled", "provider_id", "enabled"),
        Index("idx_models_type_enabled", "model_type", "enabled"),
    )

    id: int | None = Field(default=None, primary_key=True)
    provider_id: int = Field(foreign_key="providers.id", description="所属供应商 ID")
    model_key: str = Field(description="供应商内模型标识")
    display_name: str | None = Field(default=None, description="显示名称")
    model_type: str = Field(default="chat", description="模型类型")
    request_type: str = Field(default="openai_compatible", description="请求协议类型")
    capabilities: str = Field(
        default="[]",
        sa_column=Column(String, nullable=False, server_default="[]"),
        description="能力标签 JSON",
    )
    supports_streaming: bool = Field(default=True)
    supports_tools: bool = Field(default=False)
    supports_vision: bool = Field(default=False)
    supports_embedding: bool = Field(default=False)
    supports_reasoning: bool = Field(default=False)
    context_window: int | None = Field(default=None)
    max_output_tokens: int | None = Field(default=None)
    pricing_strategy: str = Field(default="token", description="计费策略")
    pricing_unit: str = Field(default="token_1k", description="计费单位")
    pricing_unit_size: float = Field(default=1000, description="每个计费单位包含的用量")
    input_price: float | None = Field(default=None, description="输入维度单价")
    output_price: float | None = Field(default=None, description="输出维度单价")
    total_price: float | None = Field(default=None, description="总量维度单价")
    flat_price: float | None = Field(default=None, description="每次请求固定价格")
    currency: str = Field(default="USD")
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_dt_now)
    updated_at: datetime = Field(default_factory=_dt_now)
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )

    @property
    def label(self) -> str:
        return self.display_name or self.model_key

    def get_capabilities(self) -> list[str]:
        try:
            data = json.loads(self.capabilities or "[]")
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    def set_capabilities(self, values: list[str]) -> None:
        self.capabilities = json.dumps(values, ensure_ascii=False)


class ProviderRepository(BaseRepository[Provider]):
    """供应商配置仓库。"""

    model = Provider

    def create_with_api_key(self, *, api_key: str | None = None, **kwargs: Any) -> Provider:
        provider = Provider(**kwargs)
        provider.set_api_key(api_key)
        return self.save(provider)

    def update_api_key(self, provider: Provider, api_key: str | None) -> Provider:
        provider.set_api_key(api_key)
        return self.save(provider)

    def get_by_key(self, provider_key: str) -> Provider | None:
        return self.get_by_field("provider_key", provider_key)

    def get_enabled(self) -> list[Provider]:
        return self.list(enabled=True, order_by="provider_key", descending=False)


class ModelRepository(BaseRepository[Model]):
    """模型配置仓库。"""

    model = Model

    def get_by_key(self, provider_id: int, model_key: str) -> Model | None:
        stmt = select(Model).where(
            Model.provider_id == provider_id,
            Model.model_key == model_key,
        )
        return self.session.exec(stmt).first()

    def get_by_provider(self, provider_id: int) -> list[Model]:
        return self.list(provider_id=provider_id, order_by="model_key", descending=False)

    def get_enabled(self) -> list[Model]:
        return self.list(enabled=True, order_by="model_key", descending=False)
