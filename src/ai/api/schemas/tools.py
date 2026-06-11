"""工具相关请求/响应 Schema。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolInfo(BaseModel):
    """工具基本信息。"""

    name: str = Field(description="工具名称")
    display_name: str = Field(description="显示名称")
    description: str = Field(description="工具描述")
    source_type: str = Field(description="来源类型（builtin/mcp/skill）")
    source_id: str | None = Field(default=None, description="来源标识")
    permissions: list[str] = Field(default_factory=list, description="权限标签")
    output_description: str | None = Field(default=None, description="输出描述")
    essential: bool = Field(default=False, description="是否为核心工具")
    enabled: bool = Field(default=True, description="是否启用")


class ToolDetail(ToolInfo):
    """工具详情（含参数 schema）。"""

    args_schema: dict[str, Any] = Field(
        default_factory=dict, description="参数 JSON Schema"
    )
    input_schema: dict[str, Any] = Field(
        default_factory=dict, description="输入 Schema（与 args_schema 一致）"
    )


class ToolExecuteRequest(BaseModel):
    """工具测试执行请求。"""

    arguments: dict[str, Any] = Field(default_factory=dict, description="工具参数")
    timeout: float | None = Field(default=None, gt=0, description="超时秒数")


class ToolExecuteResponse(BaseModel):
    """工具执行诊断响应。"""

    tool_name: str = Field(description="工具名称")
    source_type: str = Field(description="来源类型")
    source_id: str | None = Field(default=None, description="来源标识")
    status: str = Field(description="执行状态（success/failed/timeout/denied）")
    duration_ms: int = Field(default=0, description="执行耗时（毫秒）")
    permission_decision: str | None = Field(default=None, description="权限决策")
    input_summary: str | None = Field(default=None, description="输入摘要")
    output_summary: str | None = Field(default=None, description="输出摘要")
    error_type: str | None = Field(default=None, description="错误类型")
    error_message: str | None = Field(default=None, description="错误信息")
    result: Any | None = Field(default=None, description="原始执行结果")
