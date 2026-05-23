import json
from pathlib import Path

from pydantic import Field

from src.ai.config.base_config import BaseSettingsConfig, project_root


class LLMSettings(BaseSettingsConfig):
    """全局配置，从 .env 文件和环境变量自动加载。

    API Key 和 base_url 已迁移到数据库 Provider 表（加密存储），
    通过 ProviderConfigFactory 从数据库读取。
    """

    # ── 应用级 ──────────────────────────────────────────
    model_name: str = "minmax-2.7"
    request_timeout: int = 60

    # ── Token 感知上下文管理 ──────────────────────────────
    model_context_overrides: str = ""
    model_context_threshold: float = 0.8
    model_default_context_size: int = 8192

    # ── LLM 扩展配置 ──────────────────────────────────────
    llm_extra_models: str = ""

    # ── HTTP 客户端转换 ──────────────────────────────────────
    http_default_converter: str = "json"
    http_converter_modules: str = ""


class MemorySettings(BaseSettingsConfig):
    # ── Memory ────────────────────────────────────────────
    memory_backend: str = "sqlite"
    memory_persist_path: str = ""
    memory_max_short_term_messages: int = 20
    memory_summary_model: str = ""
    memory_summary_token_limit: int = 1000
    memory_enable_summary: bool = True


class MCPSettings(BaseSettingsConfig):
    """MCP 服务器配置，从 .env 自动加载。

    优先使用 MCP_CONFIG_FILE 指向的 JSON 文件，
    其次使用 MCP_SERVERS 内联 JSON。
    """

    mcp_enabled: bool = Field(default=False, description="是否启用 MCP 客户端")
    mcp_config_file: str = Field(default="", description="MCP 服务器配置 JSON 文件路径")
    mcp_servers: str = Field(
        default="{}", description="MCP 服务器配置 JSON（config_file 优先）"
    )
    mcp_server_enabled: bool = Field(
        default=False, description="是否将内置工具暴露为 MCP 服务器"
    )
    mcp_server_host: str = Field(default="127.0.0.1")
    mcp_server_port: int = Field(default=9000)
    mcp_server_transport: str = Field(default="streamable_http")

    def get_server_configs(self) -> dict:
        # 优先读配置文件
        if self.mcp_config_file.strip():
            path = Path(self.mcp_config_file)
            if not path.is_absolute():
                path = project_root / path
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        # 其次用内联 JSON
        if self.mcp_servers.strip():
            return json.loads(self.mcp_servers)
        return {}


class Settings(BaseSettingsConfig):
    """全局配置，从 .env 文件和环境变量自动加载。"""

    llm_settings: LLMSettings = LLMSettings()
    memory_settings: MemorySettings = MemorySettings()
    mcp_settings: MCPSettings = MCPSettings()


settings = Settings()
