"""MCP 配置读取仓库。"""

from __future__ import annotations

import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any
from typing import Literal

from sqlmodel import Session

from src.ai.exception.base_exception import BaseExceptions
from src.ai.storage.config_models import MCPServer
from src.ai.storage.config_models import MCPServerRepository as BaseMCPServerRepository


MCPTransport = Literal["stdio", "http", "sse", "websocket"]


class MCPConfigError(BaseExceptions):
    """MCP server 配置错误。"""


@dataclass(frozen=True)
class MCPServerConfig:
    """数据库 MCP server 配置的运行时形态。"""

    server_key: str
    transport: MCPTransport
    display_name: str | None = None
    command: str | None = None
    args: list[str] = field(default_factory=list)
    url: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    permission_policy: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class MCPConfigRepository:
    """从数据库读取 MCP server 配置。"""

    def __init__(self, session: Session) -> None:
        self._repo = BaseMCPServerRepository(session)

    def list_enabled(self) -> list[MCPServerConfig]:
        return [self._to_config(server) for server in self._repo.list(enabled=True)]

    def get_enabled(self, server_key: str) -> MCPServerConfig:
        server = self._repo.get_by_field("server_key", server_key)
        if server is None or not server.enabled:
            raise MCPConfigError("MCP server 不存在或未启用", context={"server": server_key})
        return self._to_config(server)

    def update_status(self, server_key: str, status: str) -> None:
        server = self._repo.get_by_field("server_key", server_key)
        if server is None:
            return
        self._repo.update(server, status=status, last_checked_at=datetime.now())

    def _to_config(self, server: MCPServer) -> MCPServerConfig:
        transport = server.transport
        if transport not in {"stdio", "http", "sse", "websocket"}:
            raise MCPConfigError(
                "不支持的 MCP transport",
                context={"server": server.server_key, "transport": transport},
            )

        args = _loads_json(server.args, default=[], field_name="args", server_key=server.server_key)
        env = _loads_json(server.env, default={}, field_name="env", server_key=server.server_key)
        permission_policy = _loads_json(
            server.permission_policy,
            default={},
            field_name="permission_policy",
            server_key=server.server_key,
        )
        metadata = _loads_json(
            server.extra,
            default={},
            field_name="metadata",
            server_key=server.server_key,
        )

        if transport == "stdio" and not server.command:
            raise MCPConfigError("stdio MCP server 缺少 command", context={"server": server.server_key})
        if transport in {"http", "sse", "websocket"} and not server.url:
            raise MCPConfigError("远程 MCP server 缺少 url", context={"server": server.server_key})

        return MCPServerConfig(
            server_key=server.server_key,
            display_name=server.display_name,
            transport=transport,  # type: ignore[arg-type]
            command=server.command,
            args=[str(item) for item in args],
            url=server.url,
            env={str(key): str(value) for key, value in env.items()},
            permission_policy=permission_policy,
            enabled=server.enabled,
            metadata=metadata,
        )


def _loads_json(
    value: str | None,
    *,
    default: Any,
    field_name: str,
    server_key: str,
) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise MCPConfigError(
            "MCP server JSON 配置解析失败",
            context={"server": server_key, "field": field_name},
        ) from exc
