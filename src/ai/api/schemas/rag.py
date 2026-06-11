"""RAG 相关请求/响应 Schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RagIndexFileRequest(BaseModel):
    """索引文件请求。"""

    path: str = Field(..., min_length=1, description="文件路径")
    session_id: str | None = Field(default=None, description="会话 ID")
    reindex: bool = Field(default=False, description="是否强制重新索引")


class RagIndexUrlRequest(BaseModel):
    """索引 URL 请求。"""

    url: str = Field(..., min_length=1, description="目标 URL")
    session_id: str | None = Field(default=None, description="会话 ID")
    reindex: bool = Field(default=False, description="是否强制重新索引")


class RagIndexTextRequest(BaseModel):
    """索引文本请求。"""

    text: str = Field(..., min_length=1, description="文本内容")
    title: str | None = Field(default=None, description="文档标题")
    session_id: str | None = Field(default=None, description="会话 ID")
    reindex: bool = Field(default=False, description="是否强制重新索引")


class RagIndexDirectoryRequest(BaseModel):
    """索引目录请求。"""

    path: str = Field(..., min_length=1, description="目录路径")
    patterns: list[str] | None = Field(default=None, description="文件匹配模式")
    session_id: str | None = Field(default=None, description="会话 ID")
    reindex: bool = Field(default=False, description="是否强制重新索引")


class RagSearchRequest(BaseModel):
    """RAG 搜索请求。"""

    query: str = Field(..., min_length=1, description="搜索查询")
    session_id: str | None = Field(default=None, description="会话 ID")
    top_k: int | None = Field(default=None, ge=1, le=50, description="返回结果数量")


class RagDocumentInfoResponse(BaseModel):
    """文档索引信息。"""

    source_path: str = Field(description="文件路径")
    title: str | None = Field(default=None, description="文档标题")
    chunk_count: int = Field(default=0, description="分块数量")
    mime_type: str | None = Field(default=None, description="MIME 类型")
    session_id: str | None = Field(default=None, description="会话 ID")
    scope: str = Field(default="global", description="作用域")
    collection_name: str = Field(description="集合名称")
    status: str = Field(default="active", description="文档状态")
    content_hash: str | None = Field(default=None, description="内容哈希")


class RagSearchResultResponse(BaseModel):
    """搜索结果。"""

    id: str = Field(description="文档 ID")
    source_path: str = Field(default="", description="来源路径")
    title: str = Field(default="", description="文档标题")
    content: str = Field(default="", description="匹配内容")
    chunk_index: int = Field(default=0, description="分块索引")
    score: float = Field(default=0.0, description="相似度分数")


class RagDeleteAllResponse(BaseModel):
    """删除全部响应。"""

    deleted_count: int = Field(description="删除的文档数量")


class RagStatsResponse(BaseModel):
    """RAG 统计信息。"""

    total_chunks: int = Field(default=0, description="总分块数")
    collection_name: str = Field(description="集合名称")
