"""MCP 路由。"""

from __future__ import annotations

from fastapi import APIRouter

from src.ai.api.schemas.mcp import MCPServerResponse, MCPToolResponse
from src.ai.api.services.mcp_service import MCPService

router = APIRouter()


@router.get("/servers", response_model=list[MCPServerResponse])
async def list_servers():
    servers = MCPService().list_servers()
    return [
        MCPServerResponse(
            server_key=server.server_key,
            transport=server.transport,
            display_name=server.display_name,
            enabled=server.enabled,
            metadata=server.metadata,
        )
        for server in servers
    ]


@router.get("/tools", response_model=list[MCPToolResponse])
async def list_mcp_tools(server_key: str | None = None):
    tools = await MCPService().list_tools(server_key)
    return [
        MCPToolResponse(
            server_key=tool.server_key,
            name=tool.name,
            binding_name=tool.binding_name,
            description=tool.description,
            input_schema=tool.input_schema,
        )
        for tool in tools
    ]


@router.get("/health")
async def health_check(server_key: str | None = None):
    return await MCPService().health_check(server_key)

