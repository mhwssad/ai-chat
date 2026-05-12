"""MCP 客户端管理器 — 连接外部 MCP 服务器并加载工具到 ToolRegistry。"""

import asyncio
import logging
from typing import Optional

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.ai_chat.mcp.config import mcp_settings
from src.ai_chat.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class MCPClientManager:
    """管理 MCP 服务器连接，将远程工具注入 ToolRegistry。"""

    def __init__(self) -> None:
        self._client: Optional[MultiServerMCPClient] = None
        self._mcp_tools: list[BaseTool] = []
        self._initialized: bool = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def client(self) -> Optional[MultiServerMCPClient]:
        return self._client

    @property
    def tools(self) -> list[BaseTool]:
        return list(self._mcp_tools)

    async def initialize(self) -> int:
        """连接所有 MCP 服务器，加载工具并注册到 ToolRegistry。

        Returns:
            新注册的 MCP 工具数量。
        """
        if not mcp_settings.mcp_enabled:
            logger.info("MCP 集成未启用")
            return 0

        configs = mcp_settings.get_server_configs()
        if not configs:
            logger.info("未配置任何 MCP 服务器")
            return 0

        try:
            self._client = MultiServerMCPClient(configs, tool_name_prefix=True)
            self._mcp_tools = await self._client.get_tools()

            count = 0
            for tool_obj in self._mcp_tools:
                tool_registry.register(tool_obj)
                count += 1

            self._initialized = True
            logger.info(f"MCP 工具加载完成：{count} 个工具已注册")
            return count

        except Exception as e:
            logger.error(f"MCP 初始化失败：{e}")
            return 0

    async def get_tools(self, server_name: Optional[str] = None) -> list[BaseTool]:
        if not self._client:
            return []
        if server_name:
            return await self._client.get_tools(server_name=server_name)
        return self._mcp_tools

    async def shutdown(self) -> None:
        self._mcp_tools.clear()
        self._client = None
        self._initialized = False
        logger.info("MCP 客户端已关闭")

    def run_sync(self, coro):
        """在同步上下文中运行异步协程。"""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        else:
            loop = True

        if loop:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        else:
            return asyncio.run(coro)


mcp_client_manager = MCPClientManager()
