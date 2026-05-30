"""MCP 配置读取 — 从 JSON 文件加载。"""

import json
from pathlib import Path
from typing import Any

from src.ai.core.mcp.types import MCPServerConfig
from src.ai.exception.mcp_config_exception import MCPConfigError


class MCPConfigRepository:
    """从 JSON 文件读取 MCP server 配置。

    JSON 文件路径通过 MCPSettings.mcp_config_file 配置，
    默认为项目根目录下的 mcp_servers.json。
    """

    def __init__(self, config_path: Path) -> None:
        self._path = config_path

    def list_enabled(self) -> list[MCPServerConfig]:
        """列出所有启用的 MCP server 配置。"""
        data = self._load_json()
        configs: list[MCPServerConfig] = []
        for key, value in data.items():
            config = self._to_config(key, value)
            if config.enabled:
                configs.append(config)
        return configs

    def get_enabled(self, server_key: str) -> MCPServerConfig:
        """获取指定 server 的配置（必须存在且启用）。"""
        data = self._load_json()
        if server_key not in data:
            raise MCPConfigError("MCP server 不存在", context={"server": server_key})
        config = self._to_config(server_key, data[server_key])
        if not config.enabled:
            raise MCPConfigError("MCP server 未启用", context={"server": server_key})
        return config

    def _load_json(self) -> dict[str, Any]:
        """读取并解析 JSON 文件。"""
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MCPConfigError(
                f"MCP 配置文件解析失败: {self._path}",
                context={"path": str(self._path), "error": str(exc)},
            ) from exc

    def _to_config(self, key: str, data: dict[str, Any]) -> MCPServerConfig:
        """将 JSON 条目转为 MCPServerConfig。"""
        if not isinstance(data, dict):
            raise MCPConfigError(
                "MCP server 配置必须是对象",
                context={"server": key},
            )

        transport = data.get("transport", "stdio")
        if transport not in {"stdio", "http", "sse", "websocket"}:
            raise MCPConfigError(
                "不支持的 MCP transport",
                context={"server": key, "transport": transport},
            )

        command = data.get("command")
        url = data.get("url")

        if transport == "stdio" and not command:
            raise MCPConfigError(
                "stdio MCP server 缺少 command",
                context={"server": key},
            )
        if transport in {"http", "sse", "websocket"} and not url:
            raise MCPConfigError(
                "远程 MCP server 缺少 url",
                context={"server": key, "transport": transport},
            )

        return MCPServerConfig(
            server_key=key,
            display_name=data.get("display_name"),
            transport=transport,  # type: ignore[arg-type]
            command=command,
            args=[str(item) for item in data.get("args", [])],
            url=url,
            env={str(k): str(v) for k, v in data.get("env", {}).items()},
            permission_policy=data.get("permission_policy", {}),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {}),
        )
