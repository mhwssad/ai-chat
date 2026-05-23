"""模型和供应商 API schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── 响应 ──────────────────────────────────────────────────


class ProviderResponse(BaseModel):
    id: int | None
    provider_key: str
    display_name: str | None
    base_url: str | None
    default_model_id: int | None
    enabled: bool
    status: str
    has_api_key: bool = False


class ModelResponse(BaseModel):
    id: int | None
    provider_id: int
    model_key: str
    display_name: str | None
    model_type: str
    request_type: str
    enabled: bool
    supports_streaming: bool
    supports_tools: bool
    context_window: int | None
    max_output_tokens: int | None
    currency: str


# ── Provider 请求 ──────────────────────────────────────────


class ProviderCreateRequest(BaseModel):
    """创建供应商。"""

    provider_key: str = Field(description="供应商唯一标识")
    display_name: str | None = None
    base_url: str | None = None
    api_key: str | None = Field(default=None, description="API Key（明文传入，服务端加密存储）")
    enabled: bool = True


class ProviderUpdateRequest(BaseModel):
    """更新供应商。api_key 传 None 不修改，传空串清除，传新值更新。"""

    display_name: str | None = None
    base_url: str | None = None
    api_key: str | None = Field(default=None, description="None=不修改，空串=清除，非空=更新")
    enabled: bool | None = None


# ── Model 请求 ──────────────────────────────────────────────


class ModelCreateRequest(BaseModel):
    """创建模型。"""

    provider_id: int
    model_key: str
    display_name: str | None = None
    model_type: str = "chat"
    request_type: str = "openai_compatible"
    supports_streaming: bool = True
    supports_tools: bool = False
    context_window: int | None = None
    max_output_tokens: int | None = None
    input_price: float | None = None
    output_price: float | None = None
    currency: str = "USD"
    enabled: bool = True


class ModelUpdateRequest(BaseModel):
    """更新模型。所有字段可选，None 表示不修改。"""

    provider_id: int | None = None
    model_key: str | None = None
    display_name: str | None = None
    model_type: str | None = None
    request_type: str | None = None
    supports_streaming: bool | None = None
    supports_tools: bool | None = None
    context_window: int | None = None
    max_output_tokens: int | None = None
    input_price: float | None = None
    output_price: float | None = None
    currency: str | None = None
    enabled: bool | None = None
