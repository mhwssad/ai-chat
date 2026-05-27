"""统一工具管理器。"""

from typing import Any

from langchain_core.tools import BaseTool

from .registry import ToolRegistry, tool_registry


class ToolManager:
    """组装、发现和执行统一工具池。"""

    def __init__(self, registry: ToolRegistry = tool_registry) -> None:
        self._registry = registry
        self._builtin_loaded = False

    def load_builtin_tools(self) -> None:
        """导入 builtins/ 包触发自注册（仅首次）。"""
        if self._builtin_loaded:
            return
        from . import builtins  # noqa: F401

        self._builtin_loaded = True

    async def load_mcp_tools(self, server_key: str | None = None) -> None:
        """从 MCP 发现工具并注册。返回 langchain 原生 BaseTool。"""
        from src.ai.core.mcp import mcp_manager
        from .registry import ToolMeta

        tools = await mcp_manager.discover_tools(server_key)
        for t in tools:
            self._registry.register(t, meta=ToolMeta(source_type="mcp"))

    async def refresh(self, *, include_mcp: bool = True) -> None:
        """清空注册表并重新加载所有工具。"""
        self._registry.clear()
        self._builtin_loaded = False
        self.load_builtin_tools()
        if include_mcp:
            await self.load_mcp_tools()

    def list_tools(self, *, enabled_only: bool = False) -> list[BaseTool]:
        """列出已注册工具。"""
        return self._registry.list(enabled_only=enabled_only)

    def list_tool_schemas(self, *, enabled_only: bool = True) -> list[dict[str, Any]]:
        """列出工具的 OpenAI function-calling schema。"""
        tools = self._registry.list(enabled_only=enabled_only)
        schemas: list[dict[str, Any]] = []
        for t in tools:
            params = t.args_schema.model_json_schema() if t.args_schema else {"type": "object", "properties": {}}
            schemas.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": params,
                },
            })
        return schemas

    def search_tools(self, query: str) -> list[BaseTool]:
        """按关键词搜索已启用的工具。"""
        q = query.lower()
        return [
            t for t in self._registry.list(enabled_only=True)
            if q in t.name.lower() or q in (t.description or "").lower()
        ]

    def get_tool(self, name: str) -> BaseTool:
        """按名称获取工具。"""
        return self._registry.get(name)

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        config: dict[str, Any] | None = None,
    ) -> Any:
        """查找工具并执行。"""
        tool = self._registry.get(tool_name)
        if not self._registry.get_meta(tool_name).enabled:
            from src.ai.exception.tool_exception import ToolDisabledError

            raise ToolDisabledError("工具已禁用", context={"tool": tool_name})
        return await tool.ainvoke(arguments, config=config)

tool_manager = ToolManager()
tool_manager.load_builtin_tools()
