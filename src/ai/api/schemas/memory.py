"""记忆相关请求/响应 Schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MemoryWriteRequestSchema(BaseModel):
    """保存记忆请求。"""

    content: str = Field(..., min_length=1, description="记忆内容")
    memory_type: str = Field(
        default="project", description="记忆类型（user/feedback/project/reference）"
    )
    name: str | None = Field(default=None, description="记忆名称")
    description: str | None = Field(default=None, description="描述")
    scope: str = Field(
        default="project", description="作用域（session/user/project/team）"
    )
    source_type: str = Field(
        default="manual",
        description="来源类型（manual/message/tool_result/auto_memory）",
    )
    source_id: str | None = Field(default=None, description="来源 ID")


class MemorySearchRequest(BaseModel):
    """记忆搜索请求。"""

    query: str = Field(..., min_length=1, description="搜索查询")
    limit: int = Field(default=5, ge=1, le=50, description="返回结果数量")


class MemoryExtractRequest(BaseModel):
    """从对话提取记忆请求。"""

    user_message: str = Field(..., min_length=1, description="用户消息")
    assistant_message: str = Field(..., min_length=1, description="助手消息")


class MemoryEntryResponse(BaseModel):
    """记忆条目。"""

    name: str = Field(description="记忆名称")
    memory_type: str = Field(description="记忆类型")
    description: str = Field(default="", description="描述")
    content: str = Field(description="记忆内容")
    scope: str = Field(default="project", description="作用域")
    source_type: str = Field(default="manual", description="来源类型")
    status: str = Field(default="active", description="状态")
    created_at: str | None = Field(default=None, description="创建时间")


class MemorySearchResultResponse(BaseModel):
    """记忆搜索结果。"""

    entry: MemoryEntryResponse = Field(description="记忆条目")
    score: float = Field(description="相关度分数")
    match_type: str = Field(description="匹配类型")


class MemoryStatsResponse(BaseModel):
    """记忆统计信息。"""

    total: int = Field(default=0, description="总条目数")
    by_type: dict[str, int] = Field(default_factory=dict, description="按类型统计")
    by_status: dict[str, int] = Field(default_factory=dict, description="按状态统计")
