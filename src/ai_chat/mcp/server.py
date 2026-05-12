"""MCP 服务器 — 将内置工具暴露为 MCP 协议供外部客户端调用。"""

import logging
from typing import Optional

from langchain_mcp_adapters.tools import to_fastmcp
from mcp.server.fastmcp import FastMCP

from src.ai_chat.mcp.config import mcp_settings
from src.ai_chat.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class MCPServerManager:
    """将 ai-chat 内置工具暴露为 MCP 服务器。"""

    def __init__(self) -> None:
        self._server: Optional[FastMCP] = None

    def _build_server(self) -> FastMCP:
        mcp = FastMCP("ai-chat-tools")

        for tool_obj in tool_registry.get_all():
            try:
                fastmcp_tool = to_fastmcp(tool_obj)
                mcp._tool_manager._tools[fastmcp_tool.name] = fastmcp_tool
                logger.debug(f"MCP 服务器注册工具: {fastmcp_tool.name}")
            except Exception as e:
                logger.warning(f"跳过工具 {tool_obj.name}: {e}")

        return mcp

    def start(self) -> None:
        """启动 MCP 服务器（阻塞）。"""
        self._server = self._build_server()

        transport = mcp_settings.mcp_server_transport
        logger.info(
            f"启动 MCP 服务器: transport={transport}, "
            f"host={mcp_settings.mcp_server_host}, "
            f"port={mcp_settings.mcp_server_port}"
        )

        if transport == "streamable_http":
            self._server.run(
                transport="streamable-http",
                host=mcp_settings.mcp_server_host,
                port=mcp_settings.mcp_server_port,
            )
        elif transport == "stdio":
            self._server.run(transport="stdio")
        else:
            self._server.run(
                transport="sse",
                host=mcp_settings.mcp_server_host,
                port=mcp_settings.mcp_server_port,
            )


mcp_server_manager = MCPServerManager()
