"""MCP server 管理器。"""

from __future__ import annotations

import json
import time
from functools import partial
from typing import Any

import anyio

from src.ai.storage import AuditLogRepository
from src.ai.storage.database import get_session
from src.ai.utils.redaction import redact_for_audit

from .client import MCPClient
from .tool_adapter import mcp_tools_to_bindings
from .types import MCPCallResult, MCPHealthResult, MCPTool
from src.ai.storage.mcp_repository import MCPConfigRepository, MCPServerConfig


class MCPManager:
    """管理数据库中启用的 MCP server。"""

    def list_enabled_servers(self) -> list[MCPServerConfig]:
        with get_session() as session:
            return MCPConfigRepository(session).list_enabled()

    async def discover_tools(self, server_key: str | None = None) -> list[MCPTool]:
        configs = self._load_configs(server_key)
        tools: list[MCPTool] = []
        for config in configs:
            tools.extend(await MCPClient(config).list_tools())
        return tools

    async def discover_tool_bindings(self, server_key: str | None = None):
        tools = await self.discover_tools(server_key)
        return mcp_tools_to_bindings(tools)

    async def health_check(self, server_key: str | None = None) -> list[MCPHealthResult]:
        configs = self._load_configs(server_key)
        results: list[MCPHealthResult] = []
        for config in configs:
            result = await MCPClient(config).health_check()
            self._update_status(result)
            results.append(result)
        return results

    async def call_tool(
        self,
        *,
        server_key: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        session_id: str | None = None,
        record_audit: bool = True,
    ) -> MCPCallResult:
        config = self._load_configs(server_key)[0]
        started = time.perf_counter()
        try:
            result = await MCPClient(config).call_tool(tool_name, arguments or {})
            duration_ms = int((time.perf_counter() - started) * 1000)
            if record_audit:
                self._record_call(
                    session_id=session_id,
                    server_key=server_key,
                    tool_name=tool_name,
                    arguments=arguments or {},
                    result=result,
                    duration_ms=duration_ms,
                )
            return result
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            if record_audit:
                self._record_failure(
                    session_id=session_id,
                    server_key=server_key,
                    tool_name=tool_name,
                    arguments=arguments or {},
                    exc=exc,
                    duration_ms=duration_ms,
                )
            raise

    async def list_resources(self, server_key: str) -> list[dict[str, Any]]:
        config = self._load_configs(server_key)[0]
        return await MCPClient(config).list_resources()

    async def read_resource(self, *, server_key: str, uri: str) -> dict[str, Any]:
        config = self._load_configs(server_key)[0]
        return await MCPClient(config).read_resource(uri)

    def discover_tools_sync(self, server_key: str | None = None) -> list[MCPTool]:
        return anyio.run(self.discover_tools, server_key)

    def discover_tool_bindings_sync(self, server_key: str | None = None):
        return anyio.run(self.discover_tool_bindings, server_key)

    def health_check_sync(self, server_key: str | None = None) -> list[MCPHealthResult]:
        return anyio.run(self.health_check, server_key)

    def call_tool_sync(
        self,
        *,
        server_key: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        session_id: str | None = None,
        record_audit: bool = True,
    ) -> MCPCallResult:
        return anyio.run(
            partial(
                self.call_tool,
                server_key=server_key,
                tool_name=tool_name,
                arguments=arguments,
                session_id=session_id,
                record_audit=record_audit,
            )
        )

    def list_resources_sync(self, server_key: str) -> list[dict[str, Any]]:
        return anyio.run(self.list_resources, server_key)

    def read_resource_sync(self, *, server_key: str, uri: str) -> dict[str, Any]:
        return anyio.run(partial(self.read_resource, server_key=server_key, uri=uri))

    def _load_configs(self, server_key: str | None) -> list[MCPServerConfig]:
        with get_session() as session:
            repo = MCPConfigRepository(session)
            if server_key:
                return [repo.get_enabled(server_key)]
            return repo.list_enabled()

    def _update_status(self, result: MCPHealthResult) -> None:
        status = "available" if result.status == "available" else "error"
        with get_session() as session:
            MCPConfigRepository(session).update_status(result.server_key, status)

    def _record_call(
        self,
        *,
        session_id: str | None,
        server_key: str,
        tool_name: str,
        arguments: dict[str, Any],
        result: MCPCallResult,
        duration_ms: int,
    ) -> None:
        with get_session() as session:
            AuditLogRepository(session).create(
                session_id=session_id,
                event_type="tool_call",
                source_module="mcp",
                target=f"{server_key}/{tool_name}",
                input_summary=redact_for_audit(json.dumps(arguments, ensure_ascii=False)),
                output_summary=redact_for_audit(json.dumps(result.raw, ensure_ascii=False)),
                status="failed" if result.is_error else "success",
                duration_ms=duration_ms,
            )

    def _record_failure(
        self,
        *,
        session_id: str | None,
        server_key: str,
        tool_name: str,
        arguments: dict[str, Any],
        exc: Exception,
        duration_ms: int,
    ) -> None:
        with get_session() as session:
            AuditLogRepository(session).create(
                session_id=session_id,
                event_type="tool_call",
                source_module="mcp",
                target=f"{server_key}/{tool_name}",
                input_summary=redact_for_audit(json.dumps(arguments, ensure_ascii=False)),
                status="failed",
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
                error_message=redact_for_audit(str(exc)),
            )


mcp_manager = MCPManager()
