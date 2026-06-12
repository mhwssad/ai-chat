"""MCP 状态收集器 — 收集 MCP 服务器健康状态。"""

from src.ai.config.logging_setup import get_logger
from typing import TYPE_CHECKING

from src.ai.core.context.collector import ContextCollector
from src.ai.core.context.types import (
    ContextBuildRequest,
    ContextCollectorResult,
    ContextSection,
)

if TYPE_CHECKING:
    from src.ai.core.mcp.manager import MCPManager

logger = get_logger(__name__)


class MCPCollector(ContextCollector):
    """收集 MCP 服务器健康状态。

    检查所有已启用的 MCP server 的连接状态和工具数量。
    不可缓存（服务器状态可能随时变化）。

    Args:
        mcp_manager: MCP 管理器实例。
    """

    def __init__(self, mcp_manager: "MCPManager") -> None:
        self._mcp_manager = mcp_manager

    @property
    def name(self) -> str:
        return "mcp"

    async def collect(self, request: ContextBuildRequest) -> ContextCollectorResult:
        if not request.enable_tools:
            return ContextCollectorResult()

        try:
            results = await self._mcp_manager.health_check()
            if not results:
                return ContextCollectorResult()

            available = [r for r in results if r.status == "available"]
            errors = [r for r in results if r.status == "error"]

            lines = ["## MCP 服务器状态", ""]

            if available:
                lines.append(f"可用: {len(available)} 个")
                for r in available:
                    tool_info = f" ({r.tool_count} 个工具)" if r.tool_count else ""
                    lines.append(f"  - {r.server_key}{tool_info}")

            if errors:
                lines.append(f"异常: {len(errors)} 个")
                for r in errors:
                    msg = f": {r.message}" if r.message else ""
                    lines.append(f"  - {r.server_key}{msg}")

            section = ContextSection(
                name="mcp",
                content="\n".join(lines),
                priority=3,
                cacheable=False,
            )
            return ContextCollectorResult(sections=[section])
        except Exception:
            logger.debug("MCP 状态收集失败", exc_info=True)
            return ContextCollectorResult()
