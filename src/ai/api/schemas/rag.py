"""RAG Schema。"""

from pydantic import BaseModel, Field


class RagIndexRequest(BaseModel):
    """RAG 索引请求。"""

    path: str = Field(description="文件或目录路径")
    session_id: str | None = Field(default=None, description="会话 ID")
    reindex: bool = Field(default=False, description="是否重新索引")
    patterns: list[str] | None = Field(default=None, description="文件模式列表")


class RagDocumentInfoResponse(BaseModel):
    """RAG 文档信息响应。"""

    source_path: str = Field(description="源文件路径")
    title: str = Field(description="标题")
    chunk_count: int = Field(description="分块数量")
    mime_type: str = Field(description="MIME 类型")
    session_id: str | None = Field(default=None, description="会话 ID")
    scope: str = Field(default="global", description="文档作用域")
    collection_name: str = Field(default="", description="Chroma 集合名称")
    status: str = Field(default="active", description="文档状态")
    content_hash: str | None = Field(default=None, description="内容哈希")


class RagSearchRequest(BaseModel):
    """RAG 搜索请求。"""

    query: str = Field(description="搜索查询")
    session_id: str | None = Field(default=None, description="会话 ID")
    top_k: int | None = Field(default=None, description="最大返回数量")


class RagSearchResultResponse(BaseModel):
    """RAG 搜索结果响应。"""

    id: str = Field(description="结果 ID")
    source_path: str = Field(description="源文件路径")
    title: str = Field(description="标题")
    content: str = Field(description="内容")
    chunk_index: int = Field(description="分块索引")
    score: float = Field(description="相似度分数")


class RagUrlIndexRequest(BaseModel):
    """RAG URL 索引请求。"""

    url: str = Field(description="文档 URL")
    session_id: str | None = Field(default=None, description="会话 ID")
    reindex: bool = Field(default=False, description="是否重新索引")


class RagTextIndexRequest(BaseModel):
    """RAG 文本索引请求。"""

    text: str = Field(description="原始文本内容")
    title: str | None = Field(default=None, description="文档标题")
    session_id: str | None = Field(default=None, description="会话 ID")
    reindex: bool = Field(default=False, description="是否重新索引")


class RagStatsResponse(BaseModel):
    """RAG 统计响应。"""

    total_chunks: int = Field(description="总分块数")
    collection_name: str = Field(description="集合名称")


class RagUpdateTextRequest(BaseModel):
    """更新文本索引请求。"""

    source_path: str = Field(description="原索引的 source_path")
    text: str = Field(description="新的文本内容")
    title: str | None = Field(default=None, description="文档标题")
    session_id: str | None = Field(default=None, description="会话 ID")


class RagChunkResponse(BaseModel):
    """RAG 分块响应。"""

    id: str = Field(description="分块 ID")
    content: str = Field(description="分块内容")
    chunk_index: int = Field(description="分块序号")
    metadata: dict = Field(default_factory=dict, description="元数据")


class RagDocumentDetailResponse(BaseModel):
    """RAG 文档详情响应（含 chunks）。"""

    source_path: str = Field(description="源文件路径")
    title: str = Field(description="标题")
    chunk_count: int = Field(description="分块数量")
    mime_type: str = Field(description="MIME 类型")
    session_id: str | None = Field(default=None, description="会话 ID")
    scope: str = Field(default="global", description="文档作用域")
    collection_name: str = Field(default="", description="Chroma 集合名称")
    status: str = Field(default="active", description="文档状态")
    content_hash: str | None = Field(default=None, description="内容哈希")
    chunks: list[RagChunkResponse] = Field(description="分块列表")


class RagSessionInfo(BaseModel):
    """RAG 会话信息。"""

    session_id: str = Field(description="会话 ID")
    document_count: int = Field(default=0, description="文档数量")
    total_chunks: int = Field(default=0, description="总分块数")


class RagBatchDeleteRequest(BaseModel):
    """批量删除请求。"""

    paths: list[str] = Field(description="文件路径列表")
    session_id: str | None = Field(default=None, description="会话 ID")


class RagBatchDeleteResponse(BaseModel):
    """批量删除响应。"""

    results: dict[str, bool] = Field(description="每个路径的删除结果")
    success_count: int = Field(description="成功数量")
    fail_count: int = Field(description="失败数量")


class RagGlobalStatsResponse(BaseModel):
    """RAG 全局统计响应。"""

    default_chunks: int = Field(description="默认知识库分块数")
    sessions: list[RagSessionInfo] = Field(description="会话列表")
    total_sessions: int = Field(description="总会话数")
    total_chunks: int = Field(description="总分块数")
