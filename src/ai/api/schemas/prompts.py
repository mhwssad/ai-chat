"""提示词 Schema。"""

from typing import Any

from pydantic import BaseModel, Field


class PromptCreateRequest(BaseModel):
    """提示词创建/更新请求。"""

    prompt_key: str = Field(description="提示词键")
    template: str = Field(description="模板内容")
    display_name: str | None = Field(default=None, description="显示名称")
    description: str | None = Field(default=None, description="描述")
    category: str = Field(default="general", description="分类")
    change_note: str | None = Field(default=None, description="变更说明")


class PromptResponse(BaseModel):
    """提示词响应。"""

    prompt_key: str = Field(description="提示词键")
    template: str = Field(description="模板内容")
    version: int = Field(description="版本号")
    display_name: str | None = Field(default=None, description="显示名称")
    description: str | None = Field(default=None, description="描述")
    category: str = Field(description="分类")
    enabled: bool = Field(description="是否启用")


class PromptRenderRequest(BaseModel):
    """提示词渲染请求。"""

    prompt_key: str = Field(description="提示词键")
    variables: dict[str, Any] = Field(default_factory=dict, description="变量")


class PromptRenderResponse(BaseModel):
    """提示词渲染响应。"""

    prompt_key: str = Field(description="提示词键")
    content: str = Field(description="渲染后的内容")
    version: int = Field(description="版本号")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")


class PromptUpdateRequest(BaseModel):
    """提示词部分更新请求（不改模板内容，不产生新版本）。"""

    display_name: str | None = Field(default=None, description="显示名称")
    description: str | None = Field(default=None, description="描述")
    category: str | None = Field(default=None, description="分类")
    enabled: bool | None = Field(default=None, description="是否启用")


class PromptVersionResponse(BaseModel):
    """提示词版本历史响应。"""

    id: int = Field(description="版本记录 ID")
    version: int = Field(description="版本号")
    template: str = Field(description="模板内容")
    change_note: str | None = Field(default=None, description="变更说明")


class PromptRollbackRequest(BaseModel):
    """提示词版本回滚请求。"""

    version: int = Field(description="目标版本号")
    change_note: str | None = Field(default=None, description="回滚说明")
