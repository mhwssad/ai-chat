"""工具 Schema。"""

from typing import Any

from pydantic import BaseModel, Field


class ToolMetaResponse(BaseModel):
    """工具元数据响应。"""

    name: str = Field(description="工具名称")
    display_name: str = Field(description="工具显示名称")
    description: str = Field(description="工具描述")
    source_type: str = Field(description="来源类型（builtin/mcp/skill）")
    source_id: str | None = Field(default=None, description="来源 ID")
    permissions: list[str] = Field(default_factory=list, description="权限标签")
    output_description: str | None = Field(default=None, description="输出说明")
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
    status: str = Field(default="success", description="执行状态")
    duration_ms: int = Field(default=0, description="执行耗时毫秒")
    permission_decision: str | None = Field(default=None, description="权限决策")
    input_summary: str | None = Field(default=None, description="输入摘要")
    output_summary: str | None = Field(default=None, description="输出摘要")
    error_type: str | None = Field(default=None, description="错误类型")
    error_message: str | None = Field(default=None, description="错误消息")


class ToolPermissionRequest(BaseModel):
    """工具权限检查请求。"""

    arguments: dict[str, Any] = Field(default_factory=dict, description="工具参数")


class ToolPermissionResponse(BaseModel):
    """工具权限检查响应。"""

    decision: str = Field(description="权限决策：allow / ask / deny")
    tool_name: str = Field(description="工具名称")
    permissions: list[str] = Field(default_factory=list, description="权限标签")
    reason: str = Field(description="决策原因")
    confirmed: bool | None = Field(default=None, description="用户确认结果")
    cached: bool = Field(default=False, description="是否来自确认缓存")
    context: dict[str, Any] = Field(default_factory=dict, description="扩展上下文")
