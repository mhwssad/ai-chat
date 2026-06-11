"""系统相关响应 Schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SystemStatusResponse(BaseModel):
    """运行状态摘要响应。"""

    model_key: str = Field(description="当前模型标识")
    model_backend: str = Field(description="模型后端类型")
    model_status: str = Field(description="模型配置状态")
    scheduler_running: bool = Field(description="调度器是否运行中")
    scheduler_status: str = Field(description="调度器状态标签")
    memory_count: int = Field(description="记忆条目数")
    memory_status: str = Field(description="记忆服务状态")
    tool_count: int = Field(description="工具总数")
    enabled_tool_count: int = Field(description="已启用工具数")
    tool_status: str = Field(description="工具服务状态")
    thread_pool_started: bool = Field(description="线程池是否已启动")
    thread_pool_status: str = Field(description="线程池状态标签")


class ConfigSummaryResponse(BaseModel):
    """关键配置摘要响应。"""

    rag_persist_dir: str = Field(description="RAG 持久化目录")
    rag_collection_name: str = Field(description="RAG 集合名称")
    rag_top_k: int = Field(description="RAG 检索 Top-K")
    scheduler_enabled: bool = Field(description="调度器是否启用")
    scheduler_check_interval: int = Field(description="调度器检查间隔（秒）")
    thread_pool_io: int = Field(description="IO 线程池大小")
    thread_pool_cpu: int = Field(description="CPU 线程池大小")
    thread_pool_bg: int = Field(description="后台线程池大小")
    image_output_dir: str = Field(description="图像输出目录")
    tts_output_dir: str = Field(description="TTS 输出目录")
