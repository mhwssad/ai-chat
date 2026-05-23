"""单个 MCP server 客户端封装。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.websocket import websocket_client

from .errors import (
    MCPConnectionError,
    MCPProtocolError,
    MCPToolCallError,
    MCPToolDiscoveryError,
)
from .types import MCPCallResult, MCPHealthResult, MCPTool
from src.ai.storage.mcp_repository import MCPServerConfig


class MCPClient:
    """负责连接、发现和调用单个 MCP server。"""

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config

    async def health_check(self) -> MCPHealthResult:
        try:
            tools = await self.list_tools()
        except Exception as exc:
            return MCPHealthResult(
                server_key=self.config.server_key,
                status="error",
                message=str(exc),
            )
        return MCPHealthResult(
            server_key=self.config.server_key,
            status="available",
            tool_count=len(tools),
        )

    async def list_tools(self) -> list[MCPTool]:
        try:
            async with self._session() as session:
                result = await session.list_tools()
        except Exception as exc:
            raise MCPToolDiscoveryError(
                "MCP 工具发现失败",
                context={"server": self.config.server_key, "error": str(exc)},
            ) from exc

        return [self._to_tool(tool) for tool in result.tools]

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> MCPCallResult:
        try:
            async with self._session() as session:
                result = await session.call_tool(tool_name, arguments or {})
        except Exception as exc:
            raise MCPToolCallError(
                "MCP 工具调用失败",
                context={
                    "server": self.config.server_key,
                    "tool": tool_name,
                    "error": str(exc),
                },
            ) from exc

        return MCPCallResult(
            server_key=self.config.server_key,
            tool_name=tool_name,
            content=_dump_content(result.content),
            structured_content=result.structuredContent,
            is_error=bool(result.isError),
            raw=_model_dump(result),
        )

    async def list_resources(self) -> list[dict[str, Any]]:
        try:
            async with self._session() as session:
                result = await session.list_resources()
        except Exception as exc:
            raise MCPProtocolError(
                "MCP 资源列表读取失败",
                context={"server": self.config.server_key, "error": str(exc)},
            ) from exc
        return [_model_dump(resource) for resource in result.resources]

    async def read_resource(self, uri: str) -> dict[str, Any]:
        try:
            async with self._session() as session:
                result = await session.read_resource(uri)  # type: ignore[arg-type]
        except Exception as exc:
            raise MCPProtocolError(
                "MCP 资源读取失败",
                context={"server": self.config.server_key, "uri": uri, "error": str(exc)},
            ) from exc
        return _model_dump(result)

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[ClientSession]:
        try:
            async with self._transport() as streams:
                read_stream, write_stream = streams[0], streams[1]
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session
        except (MCPToolCallError, MCPToolDiscoveryError):
            raise
        except Exception as exc:
            raise MCPConnectionError(
                "MCP server 连接失败",
                context={"server": self.config.server_key, "error": str(exc)},
            ) from exc

    @asynccontextmanager
    async def _transport(self):
        if self.config.transport == "stdio":
            params = StdioServerParameters(
                command=self.config.command or "",
                args=self.config.args,
                env=self.config.env or None,
            )
            async with stdio_client(params) as streams:
                yield streams
            return

        if self.config.transport == "sse":
            async with sse_client(self.config.url or "") as streams:
                yield streams
            return

        if self.config.transport == "http":
            async with streamablehttp_client(self.config.url or "") as streams:
                yield streams
            return

        if self.config.transport == "websocket":
            async with websocket_client(self.config.url or "") as streams:
                yield streams
            return

        raise MCPProtocolError(
            "不支持的 MCP transport",
            context={"server": self.config.server_key, "transport": self.config.transport},
        )

    def _to_tool(self, tool: Any) -> MCPTool:
        raw = _model_dump(tool)
        return MCPTool(
            server_key=self.config.server_key,
            name=tool.name,
            description=tool.description or "",
            input_schema=tool.inputSchema or {"type": "object", "properties": {}},
            output_schema=tool.outputSchema,
            permission_policy=self.config.permission_policy,
            metadata={
                "title": getattr(tool, "title", None) or "",
                "annotations": raw.get("annotations") or {},
                "server_display_name": self.config.display_name or self.config.server_key,
            },
        )


def _dump_content(content: Any) -> list[Any]:
    if not isinstance(content, list):
        return [_model_dump(content)]
    return [_model_dump(item) for item in content]


def _model_dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, exclude_none=True)
    if isinstance(value, dict):
        return value
    return value
