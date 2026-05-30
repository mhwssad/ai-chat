"""统一工具管理器 — 生命周期编排、执行与 schema 格式化。"""

from typing import Any

from src.ai.core.tools.register import _set_active_registry
from src.ai.core.tools.registry import ToolMeta, ToolRegistry


class ToolManager:
    """工具生命周期管理器。

    职责：内置工具加载、刷新、执行、schema 格式化。
    查询操作（list / search / get）直接使用 ToolRegistry。
    Skills 工具由各模块自行注册。
    """

    def __init__(
        self,
        registry: ToolRegistry,
        *,
        http_aclient: object,
        mcp_manager: object,
    ) -> None:
        self._registry = registry
        self._http_aclient = http_aclient
        self._mcp_manager = mcp_manager
        self._builtin_loaded = False

    # ── 生命周期 ────────────────────────────────────────────

    def load_builtin_tools(self) -> None:
        """导入 builtins/ 包触发自注册（仅首次）。"""
        if self._builtin_loaded:
            return
        _set_active_registry(self._registry)
        from . import builtins  # noqa: F401

        builtins.register_dependent_tools(
            http_aclient=self._http_aclient,
            mcp_manager=self._mcp_manager,
            registry=self._registry,
        )

        # 注册 MCP 内置工具
        from src.ai.core.mcp.tools import create_mcp_tools

        for tool in create_mcp_tools(self._mcp_manager):
            self._registry.register(
                tool,
                meta=ToolMeta(source_type="builtin", permissions=["external_service"]),
            )

        self._builtin_loaded = True

    async def refresh(self) -> None:
        """清空注册表并重新加载内置工具。"""
        self._registry.clear()
        self._builtin_loaded = False
        self.load_builtin_tools()

    # ── 执行 ────────────────────────────────────────────────

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

    # ── 格式化 ──────────────────────────────────────────────

    def list_schemas(self, *, enabled_only: bool = True) -> list[dict[str, Any]]:
        """列出工具的 OpenAI function-calling schema。"""
        tools = self._registry.list(enabled_only=enabled_only)
        schemas: list[dict[str, Any]] = []
        for t in tools:
            params = (
                t.args_schema.model_json_schema()
                if t.args_schema
                else {"type": "object", "properties": {}}
            )
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": params,
                    },
                }
            )
        return schemas
