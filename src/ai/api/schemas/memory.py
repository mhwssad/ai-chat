"""记忆 Schema。"""

from typing import Any

from pydantic import BaseModel, Field


class MemoryCreateRequest(BaseModel):
    """记忆创建请求。"""

    content: str = Field(description="记忆内容")
    memory_type: str = Field(
        default="project", description="记忆类型（user/feedback/project/reference）"
    )
    scope: str = Field(default="project", description="作用域（session/user/project/team）")
    source_type: str = Field(
        default="manual",
        description="来源类型（message/tool_result/manual/auto_memory/team_memory）",
    )
    source_id: str | None = Field(default=None, description="来源 ID")
    name: str | None = Field(default=None, description="记忆名称（自动生成）")
    description: str | None = Field(default=None, description="记忆描述")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class MemoryEntryResponse(BaseModel):
    """记忆条目响应。"""

    name: str = Field(description="记忆名称")
    memory_type: str = Field(description="记忆类型")
    description: str = Field(description="记忆描述")
    content: str = Field(description="记忆内容")
    file_path: str | None = Field(default=None, description="文件路径")
    session_id: str | None = Field(default=None, description="会话 ID")
    scope: str = Field(default="project", description="作用域")
    source_type: str = Field(default="manual", description="来源类型")
    source_id: str | None = Field(default=None, description="来源 ID")
    status: str = Field(default="active", description="状态")
    created_at: str | None = Field(default=None, description="创建时间")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class MemoryStatusRequest(BaseModel):
    """记忆状态请求。"""

    status: str = Field(description="状态（active/disabled）")


class MemorySearchRequest(BaseModel):
    """记忆搜索请求。"""

    query: str = Field(description="搜索关键词")
    limit: int = Field(default=5, description="最大返回数量")


class MemorySearchResultResponse(BaseModel):
    """记忆搜索结果响应。"""

    entry: MemoryEntryResponse = Field(description="记忆条目")
    score: float = Field(description="相关度分数")
    match_type: str = Field(description="匹配类型")


class MemoryStatsResponse(BaseModel):
    """记忆统计响应。"""

    total: int = Field(description="总数")
    by_type: dict[str, int] = Field(description="按类型统计")
