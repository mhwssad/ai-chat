"""工具 Schema。"""

from typing import Any

from pydantic import BaseModel, Field


class ToolMetaResponse(BaseModel):
    """工具元数据响应。"""

    name: str = Field(description="工具名称")
    description: str = Field(description="工具描述")
    source_type: str = Field(description="来源类型（builtin/mcp/skill）")
    source_id: str | None = Field(default=None, description="来源 ID")
    permissions: list[str] = Field(default_factory=list, description="权限标签")
    essential: bool = Field(default=False, description="是否必要工具")
    enabled: bool = Field(default=True, description="是否启用")


class ToolSchemaResponse(BaseModel):
    """工具 OpenAI function-calling schema 响应。"""

    type: str = Field(description="类型")
    function: dict[str, Any] = Field(description="函数定义")


class ToolExecuteRequest(BaseModel):
    """工具执行请求。"""

    arguments: dict[str, Any] = Field(default_factory=dict, description="工具参数")


class ToolExecuteResponse(BaseModel):
    """工具执行响应。"""

    result: Any = Field(description="执行结果")
    tool_name: str = Field(description="工具名称")
