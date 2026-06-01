"""MCP 适配器 — MCPServerConfig 与 langchain-mcp-adapters 格式互转。"""

from typing import Any

from .types import MCPServerConfig


def to_langchain_connections(
    configs: list[MCPServerConfig],
) -> dict[str, dict[str, Any]]:
    """将 MCPServerConfig 列表转为 langchain-mcp-adapters 的 Connection 格式。

    Args:
        configs: MCP server 配置列表。

    Returns:
        可直接传给 MultiServerMCPClient 的 connections 字典。
    """
    connections: dict[str, dict[str, Any]] = {}
    for config in configs:
        conn: dict[str, Any] = {"transport": config.transport}
        if config.command:
            conn["command"] = config.command
        if config.args:
            conn["args"] = config.args
        if config.url:
            conn["url"] = config.url
        if config.env:
            conn["env"] = config.env
        connections[config.server_key] = conn
    return connections
