"""MCP 资源工具 — 提供 MCP 服务器资源列表和读取能力。"""

import json

from langchain_core.tools import BaseTool, StructuredTool


def create_list_mcp_resources_tool(mcp_manager) -> BaseTool:
    """工厂函数：创建绑定了 mcp_manager 的 list_mcp_resources 工具。"""

    async def list_mcp_resources(server_key: str) -> str:
        """列出 MCP 服务器可用资源。

        Args:
            server_key: MCP 服务器标识。
        """
        resources = await mcp_manager.list_resources(server_key)
        return json.dumps(resources, ensure_ascii=False, indent=2)

    return StructuredTool.from_function(
        coroutine=list_mcp_resources,
        name="list_mcp_resources",
    )


def create_read_mcp_resource_tool(mcp_manager) -> BaseTool:
    """工厂函数：创建绑定了 mcp_manager 的 read_mcp_resource 工具。"""

    async def read_mcp_resource(server_key: str, uri: str) -> str:
        """从 MCP 服务器读取资源。

        Args:
            server_key: MCP 服务器标识。
            uri: 资源 URI。
        """
        result = await mcp_manager.read_resource(server_key=server_key, uri=uri)
        return (
            json.dumps(result, ensure_ascii=False, indent=2)
            if not isinstance(result, str)
            else result
        )

    return StructuredTool.from_function(
        coroutine=read_mcp_resource,
        name="read_mcp_resource",
    )


def create_mcp_tools(mcp_manager) -> list[BaseTool]:
    """创建所有 MCP 内置工具。

    Args:
        mcp_manager: MCP 管理器实例。

    Returns:
        MCP 内置工具列表。
    """
    return [
        create_list_mcp_resources_tool(mcp_manager),
        create_read_mcp_resource_tool(mcp_manager),
    ]
