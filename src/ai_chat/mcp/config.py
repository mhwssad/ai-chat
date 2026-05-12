"""MCP 配置 — 从 .env 或 JSON 文件加载 MCP 服务器连接定义。"""

import json
from pathlib import Path

from pydantic import Field

from src.ai_chat.config.base_config import BaseSettingsConfig, project_root


class MCPSettings(BaseSettingsConfig):
    """MCP 服务器配置，从 .env 自动加载。

    优先使用 MCP_CONFIG_FILE 指向的 JSON 文件，
    其次使用 MCP_SERVERS 内联 JSON。
    """

    mcp_enabled: bool = Field(default=False, description="是否启用 MCP 客户端")
    mcp_config_file: str = Field(default="", description="MCP 服务器配置 JSON 文件路径")
    mcp_servers: str = Field(default="{}", description="MCP 服务器配置 JSON（config_file 优先）")
    mcp_server_enabled: bool = Field(default=False, description="是否将内置工具暴露为 MCP 服务器")
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


mcp_settings = MCPSettings()
