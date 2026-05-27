from pydantic import Field

from src.ai.config.base_config import BaseSettingsConfig


class LLMSettings(BaseSettingsConfig):
    """LLM 全局配置。"""

    model_name: str = "minmax-2.7"
    request_timeout: int = 60
    max_input_tokens: int = 128000
    max_output_tokens: int = 4096


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

    # RAG 优化检索
    rag_optimize_query: bool = True
    rag_merge_strategy: str = "deduplicate"
    rag_context_top_k: int = 5

    # 对话历史文件存储
    history_file_enabled: bool = True


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


class Settings(BaseSettingsConfig):
    """全局配置。"""

    llm: LLMSettings = LLMSettings()
    rag: RAGSettings = RAGSettings()
    memory: MemorySettings = MemorySettings()
    skills: SkillSettings = SkillSettings()
    mcp: MCPSettings = MCPSettings()


settings = Settings()
