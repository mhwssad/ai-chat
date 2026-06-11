"""模型配置相关请求/响应 Schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderConfigCreateRequest(BaseModel):
    """创建供应商请求。"""

    provider_key: str = Field(..., min_length=1, description="供应商标识")
    display_name: str | None = Field(default=None, description="显示名称")
    provider_type: str = Field(..., description="供应商类型")
    api_base: str | None = Field(default=None, description="API 基础地址")
    api_key: str | None = Field(
        default=None, description="API 密钥（明文，内部加密存储）"
    )
    enabled: bool = Field(default=True, description="是否启用")


class ProviderConfigUpdateRequest(BaseModel):
    """更新供应商请求。"""

    display_name: str | None = Field(default=None, description="显示名称")
    provider_type: str | None = Field(default=None, description="供应商类型")
    api_base: str | None = Field(default=None, description="API 基础地址")
    api_key: str | None = Field(
        default=None, description="API 密钥（明文，内部加密存储）"
    )
    enabled: bool | None = Field(default=None, description="是否启用")


class ModelConfigCreateRequest(BaseModel):
    """创建模型请求。"""

    model_key: str = Field(..., min_length=1, description="模型标识")
    provider_key: str = Field(..., min_length=1, description="所属供应商标识")
    model_type: str = Field(..., description="模型类型（chat/embedding/image/tts）")
    display_name: str | None = Field(default=None, description="显示名称")
    model_name: str = Field(..., min_length=1, description="模型名称")
    context_window: int | None = Field(default=None, description="上下文窗口大小")
    is_default: bool = Field(default=False, description="是否为默认模型")
    enabled: bool = Field(default=True, description="是否启用")


class ModelConfigUpdateRequest(BaseModel):
    """更新模型请求。"""

    provider_key: str | None = Field(default=None, description="供应商标识")
    model_type: str | None = Field(default=None, description="模型类型")
    display_name: str | None = Field(default=None, description="显示名称")
    model_name: str | None = Field(default=None, description="模型名称")
    context_window: int | None = Field(default=None, description="上下文窗口大小")
    is_default: bool | None = Field(default=None, description="是否为默认模型")
    enabled: bool | None = Field(default=None, description="是否启用")


class ProviderConfigResponse(BaseModel):
    """供应商配置响应。"""

    provider_key: str = Field(description="供应商标识")
    display_name: str | None = Field(default=None, description="显示名称")
    provider_type: str = Field(description="供应商类型")
    api_base: str | None = Field(default=None, description="API 基础地址")
    has_api_key: bool = Field(default=False, description="是否配置了 API Key")
    enabled: bool = Field(default=True, description="是否启用")


class ModelConfigResponse(BaseModel):
    """模型配置响应。"""

    model_key: str = Field(description="模型标识")
    provider_key: str = Field(description="所属供应商标识")
    model_type: str = Field(description="模型类型")
    display_name: str | None = Field(default=None, description="显示名称")
    model_name: str = Field(description="模型名称")
    context_window: int | None = Field(default=None, description="上下文窗口大小")
    is_default: bool = Field(default=False, description="是否为默认模型")
    enabled: bool = Field(default=True, description="是否启用")


class ModelTestResponse(BaseModel):
    """模型连通性测试响应。"""

    model_key: str = Field(description="模型标识")
    success: bool = Field(description="是否连通")
    latency_ms: int | None = Field(default=None, description="延迟毫秒")
    error: str | None = Field(default=None, description="错误信息")
