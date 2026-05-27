"""MCP 资源工具。"""

import json

from langchain_core.tools import tool

from src.ai.core.tools.registry import register_tool


@tool
async def list_mcp_resources(server_key: str) -> str:
    """列出 MCP 服务器可用资源。

    Args:
        server_key: MCP 服务器标识。
    """
    from src.ai.core.mcp import mcp_manager

    resources = await mcp_manager.list_resources(server_key)
    return json.dumps(resources, ensure_ascii=False, indent=2)


@tool
async def read_mcp_resource(server_key: str, uri: str) -> str:
    """从 MCP 服务器读取资源。

    Args:
        server_key: MCP 服务器标识。
        uri: 资源 URI。
    """
    from src.ai.core.mcp import mcp_manager

    result = await mcp_manager.read_resource(server_key=server_key, uri=uri)
    return json.dumps(result, ensure_ascii=False, indent=2) if not isinstance(result, str) else result


# ── 自注册 ──────────────────────────────────────────────────────────────────

register_tool(list_mcp_resources, source_type="builtin", permissions=["external_service"])
register_tool(read_mcp_resource, source_type="builtin", permissions=["external_service"])
