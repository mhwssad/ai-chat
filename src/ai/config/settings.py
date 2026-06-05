from pydantic import Field

from src.ai.config.base_config import BaseSettingsConfig
from src.ai.config.loader_settings import LoaderSettings


class RAGSettings(BaseSettingsConfig):
    """RAG 检索配置。"""

    rag_persist_dir: str = "data/chroma"
    rag_collection_name: str = "rag_documents"
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 120
    rag_top_k: int = 5
    rag_fallback_dimension: int = 384
    rag_index_patterns: str = (
        "**/*.md,**/*.txt,**/*.py,**/*.json,**/*.yaml,**/*.yml,**/*.pdf,**/*.docx"
    )
    # 查询优化
    rag_optimize_query: bool = True
    rag_merge_strategy: str = "deduplicate"
    rag_context_top_k: int = 5


class MemorySettings(BaseSettingsConfig):
    """记忆模块配置。"""

    memory_dir: str = "data/memory"
    memory_enable_auto_extract: bool = True
    memory_max_entries: int = 200

    # 对话历史
    history_table_name: str = "chat_message_store"
    history_max_messages: int = 1000

    # Compression 策略参数
    compression_max_messages: int = 30
    compression_keep_recent: int = 10
    compression_batch_size: int = 20

    # 对话历史文件存储
    history_file_enabled: bool = True

    # 全量压缩阈值（消息数超过此值触发 FullCompact）
    full_compact_threshold: int = 100

    # LLM 相关记忆选择
    relevance_max_results: int = 5
    relevance_enabled: bool = True

    # MicroCompact 工具结果最大字符数
    micro_compact_max_tool_chars: int = 4000


class SkillSettings(BaseSettingsConfig):
    """技能发现配置。"""

    skill_dirs: str = ""
    skill_auto_discover: bool = True


class MCPSettings(BaseSettingsConfig):
    """MCP 服务器配置。"""

    mcp_enabled: bool = Field(default=False, description="是否启用 MCP 客户端")
    mcp_config_file: str = Field(
        default="mcp_servers.json", description="MCP 服务器配置 JSON 文件路径"
    )
    mcp_server_enabled: bool = Field(
        default=False, description="是否将内置工具暴露为 MCP 服务器"
    )
    mcp_server_host: str = "127.0.0.1"
    mcp_server_port: int = 9000
    mcp_server_transport: str = "streamable_http"


class SchedulerSettings(BaseSettingsConfig):
    """定时任务调度器配置。"""

    scheduler_enabled: bool = Field(default=True, description="是否启用定时任务调度器")
    scheduler_max_concurrent: int = Field(default=5, description="最大并发执行任务数")
    scheduler_check_interval: int = Field(default=30, description="任务检查间隔（秒）")
    scheduler_default_max_retries: int = Field(
        default=3, description="默认最大重试次数"
    )
    scheduler_task_timeout: int = Field(
        default=300, description="单个任务执行超时（秒）"
    )
    scheduler_cleanup_days: int = Field(
        default=30, description="自动清理多少天前的执行日志"
    )


class ThreadPoolSettings(BaseSettingsConfig):
    """统一线程池配置。"""

    io_size: int = Field(default=16, description="IO 密集型线程池大小")
    cpu_size: int = Field(default=4, description="CPU 密集型线程池大小")
    bg_size: int = Field(default=4, description="后台任务线程池大小")
    shutdown_timeout: float = Field(default=30.0, description="优雅关闭超时（秒）")


class Settings(BaseSettingsConfig):
    """全局配置。"""

    rag: RAGSettings = RAGSettings()
    memory: MemorySettings = MemorySettings()
    skills: SkillSettings = SkillSettings()
    mcp: MCPSettings = MCPSettings()
    loader: LoaderSettings = LoaderSettings()
    scheduler: SchedulerSettings = SchedulerSettings()
    thread_pool: ThreadPoolSettings = ThreadPoolSettings()


# 模块级单例 — 项目内统一通过 from src.ai.config.settings import settings 获取
settings = Settings()
