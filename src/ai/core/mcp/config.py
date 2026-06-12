"""MCP 配置读取 — 优先从数据库读取，兼容 JSON 回退。"""

from __future__ import annotations

import json
from src.ai.config.logging_setup import get_logger
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from src.ai.core.mcp.types import MCPServerConfig
from src.ai.exception.mcp_config_exception import MCPConfigError
from src.ai.storage.config_models import MCPServerRecord
from src.ai.storage.config_repository import MCPServerRepository

logger = get_logger(__name__)


class MCPConfigRepository:
    """读取 MCP server 配置。

    优先使用正式配置表 mcp_servers；当表中没有任何配置或数据库不可用时，
    回退读取 mcp_servers.json，保留旧配置兼容性。
    """

    def __init__(
        self,
        config_path: Path,
        *,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        self._path = config_path
        self._session_factory = session_factory

    def list_all(self) -> list[MCPServerConfig]:
        """列出所有 MCP server 配置。"""
        db_configs = self._load_db_configs()
        if db_configs is not None:
            return db_configs

        data = self._load_json()
        return [self._to_config(key, value) for key, value in data.items()]

    def list_enabled(self) -> list[MCPServerConfig]:
        """列出所有启用的 MCP server 配置。"""
        return [config for config in self.list_all() if config.enabled]

    def get_enabled(self, server_key: str) -> MCPServerConfig:
        """获取指定 server 的配置（必须存在且启用）。"""
        configs = {config.server_key: config for config in self.list_all()}
        if server_key not in configs:
            raise MCPConfigError("MCP server 不存在", context={"server": server_key})
        config = configs[server_key]
        if not config.enabled:
            raise MCPConfigError("MCP server 未启用", context={"server": server_key})
        return config

    def _load_db_configs(self) -> list[MCPServerConfig] | None:
        """从数据库读取配置；无记录或不可用时返回 None 触发 JSON 回退。"""
        if self._session_factory is None:
            return None

        try:
            with self._session_factory() as session:
                records = MCPServerRepository(session).list(
                    limit=1000,
                    order_by="server_key",
                    descending=False,
                )
        except SQLAlchemyError:
            logger.debug("MCP 数据库配置读取失败，回退 JSON 文件", exc_info=True)
            return None

        if not records:
            return None
        return [self._record_to_config(record) for record in records]

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

    def _record_to_config(self, record: MCPServerRecord) -> MCPServerConfig:
        """将数据库记录转为 MCPServerConfig。"""
        data = {
            "display_name": record.display_name,
            "transport": record.transport,
            "command": record.command,
            "args": self._parse_json(record.args_json, default=[]),
            "url": record.url,
            "env": self._parse_json(record.env_json, default={}),
            "permission_policy": self._parse_json(
                record.permission_policy_json,
                default={},
            ),
            "enabled": record.enabled,
            "metadata": self._parse_json(record.extra, default={}),
        }
        return self._to_config(record.server_key, data)

    def _parse_json(self, raw: str | None, *, default: Any) -> Any:
        """解析数据库 JSON 字段，失败时抛出配置错误。"""
        if raw is None or raw == "":
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MCPConfigError(
                "MCP 数据库配置 JSON 字段解析失败",
                context={"error": str(exc)},
            ) from exc
