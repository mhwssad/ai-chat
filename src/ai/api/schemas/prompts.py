"""提示词相关请求/响应 Schema。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PromptSaveRequest(BaseModel):
    """保存/创建提示词模板请求。"""

    prompt_key: str = Field(..., min_length=1, description="模板唯一键")
    template: str = Field(..., min_length=1, description="Jinja2 模板内容")
    display_name: str | None = Field(default=None, description="显示名称")
    description: str | None = Field(default=None, description="描述")
    category: str = Field(default="general", description="分类")
    change_note: str | None = Field(default=None, description="变更说明")


class PromptUpdateRequest(BaseModel):
    """更新提示词模板请求。"""

    display_name: str | None = Field(default=None, description="显示名称")
    description: str | None = Field(default=None, description="描述")
    category: str | None = Field(default=None, description="分类")
    enabled: bool | None = Field(default=None, description="是否启用")


class PromptRenderRequestSchema(BaseModel):
    """渲染提示词模板请求。"""

    prompt_key: str = Field(..., min_length=1, description="模板键")
    variables: dict[str, Any] = Field(default_factory=dict, description="模板变量")


class PromptRollbackRequest(BaseModel):
    """回滚提示词模板请求。"""

    version: int = Field(..., ge=1, description="目标版本号")
    change_note: str | None = Field(default=None, description="回滚说明")


class PromptDataResponse(BaseModel):
    """提示词模板数据。"""

    prompt_key: str = Field(description="模板唯一键")
    template: str = Field(description="模板内容")
    version: int = Field(default=1, description="当前版本")
    display_name: str | None = Field(default=None, description="显示名称")
    description: str | None = Field(default=None, description="描述")
    category: str = Field(default="general", description="分类")
    enabled: bool = Field(default=True, description="是否启用")


class PromptVersionResponse(BaseModel):
    """提示词版本数据。"""

    id: int = Field(description="版本 ID")
    prompt_id: int = Field(description="模板 ID")
    version: int = Field(description="版本号")
    template: str = Field(description="模板内容")
    change_note: str | None = Field(default=None, description="变更说明")


class PromptRenderResultResponse(BaseModel):
    """渲染结果。"""

    prompt_key: str = Field(description="模板键")
    content: str = Field(description="渲染后内容")
    version: int = Field(description="使用的模板版本")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")
