"""统一工具管理器 — 生命周期编排、执行与 schema 格式化。"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from src.ai.core.tools.register import _set_active_registry
from src.ai.core.tools.registry import ToolRegistry
from src.ai.core.tools.types import ToolPlugin, ToolProgress

if TYPE_CHECKING:
    from src.ai.core.tools.permissions import ConfirmHandler, PermissionChecker

logger = logging.getLogger(__name__)


class ToolManager:
    """工具生命周期管理器。

    职责：内置工具加载、刷新、执行、schema 格式化。
    查询操作（list / search / get）直接使用 ToolRegistry。

    插件机制：实现 ToolPlugin 接口的模块可通过 register_plugin 注册，
    在 load_builtin_tools 时自动调用所有插件的 register_tools 方法。
    """

    def __init__(
        self,
        registry: ToolRegistry,
        *,
        http_aclient: object,
        model_service: object | None = None,
        permission_checker: PermissionChecker | None = None,
    ) -> None:
        self._registry = registry
        self._http_aclient = http_aclient
        self._model_service = model_service
        self._builtin_loaded = False
        self._plugins: list[ToolPlugin] = []
        self._permission_checker = permission_checker

    # ── 权限管理 ────────────────────────────────────────────

    def set_confirm_handler(self, handler: ConfirmHandler | None) -> None:
        """设置权限确认回调。UI 层通过此方法注册用户确认逻辑。

        Args:
            handler: 确认回调函数，None 表示清除。
        """
        if self._permission_checker is not None:
            self._permission_checker.set_confirm_handler(handler)

    # ── 插件管理 ────────────────────────────────────────────

    def register_plugin(self, plugin: ToolPlugin) -> None:
        """注册工具插件。

        Args:
            plugin: 实现 ToolPlugin 接口的插件实例。
        """
        self._plugins.append(plugin)

    # ── 生命周期 ────────────────────────────────────────────

    def load_builtin_tools(
        self, *, scheduler_service: object | None = None
    ) -> None:
        """导入 builtins/ 包触发自注册（仅首次）。

        Args:
            scheduler_service: 定时任务服务实例（可选）。
        """
        if self._builtin_loaded:
            return
        _set_active_registry(self._registry)
        from . import builtins  # noqa: F401

        builtins.register_dependent_tools(
            http_aclient=self._http_aclient,
            registry=self._registry,
            model_service=self._model_service,
            scheduler_service=scheduler_service,
        )

        # 执行所有插件的注册
        for plugin in self._plugins:
            plugin.register_tools(self._registry)

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
        timeout: float | None = None,
    ) -> Any:
        """查找工具并执行。

        Args:
            tool_name: 工具名称。
            arguments: 工具参数。
            config: LangChain 工具配置。
            timeout: 超时秒数，None 使用默认值（120 秒）。

        Returns:
            工具执行结果。

        Raises:
            ToolDisabledError: 工具已禁用。
            ToolPermissionError: 权限校验失败。
            ToolExecutionError: 执行超时或其他错误。
        """
        from src.ai.exception.tool_exception import (
            ToolDisabledError,
            ToolExecutionError,
        )

        tool = self._registry.get(tool_name)
        if not self._registry.get_meta(tool_name).enabled:
            raise ToolDisabledError("工具已禁用", context={"tool": tool_name})

        # 权限校验
        if self._permission_checker is not None:
            await self._permission_checker.check(tool_name, arguments)

        # 带超时执行
        effective_timeout = timeout if timeout is not None else 120.0
        try:
            return await asyncio.wait_for(
                tool.ainvoke(arguments, config=config),  # type: ignore[arg-type]
                timeout=effective_timeout,
            )
        except TimeoutError:
            raise ToolExecutionError(
                f"工具 {tool_name} 执行超时 ({effective_timeout}s)",
                context={"tool": tool_name, "timeout": effective_timeout},
            )

    # ── 流式执行 ──────────────────────────────────────────────

    async def execute_stream(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        config: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> AsyncIterator[ToolProgress]:
        """流式执行工具，返回进度事件。

        如果工具实现了 StreamableTool 协议，使用 ainvoke_stream()；
        否则回退到普通 execute() 并包装为单个完成事件。

        Args:
            tool_name: 工具名称。
            arguments: 工具参数。
            config: LangChain 工具配置。
            timeout: 超时秒数。

        Yields:
            ToolProgress 进度事件。
        """
        from src.ai.exception.tool_exception import ToolDisabledError

        tool = self._registry.get(tool_name)
        if not self._registry.get_meta(tool_name).enabled:
            raise ToolDisabledError("工具已禁用", context={"tool": tool_name})

        # 权限校验
        if self._permission_checker is not None:
            await self._permission_checker.check(tool_name, arguments)

        # 检测是否支持流式
        if hasattr(tool, "ainvoke_stream"):
            effective_timeout = timeout if timeout is not None else 120.0
            try:
                async with asyncio.timeout(effective_timeout):
                    async for progress in tool.ainvoke_stream(arguments, config=config):
                        yield progress
            except TimeoutError:
                yield ToolProgress(
                    tool_name=tool_name,
                    stage="error",
                    message=f"工具 {tool_name} 执行超时 ({effective_timeout}s)",
                )
        else:
            # 回退到普通执行
            try:
                result = await self.execute(
                    tool_name, arguments, config=config, timeout=timeout
                )
                result_str = str(result) if not isinstance(result, str) else result
                yield ToolProgress(
                    tool_name=tool_name,
                    stage="completed",
                    message="执行完成",
                    progress=1.0,
                    partial_result=result_str,
                )
            except Exception as e:
                yield ToolProgress(
                    tool_name=tool_name,
                    stage="error",
                    message=str(e),
                )

    # ── 格式化 ──────────────────────────────────────────────

    def list_schemas(self, *, enabled_only: bool = True) -> list[dict[str, Any]]:
        """列出工具的 OpenAI function-calling schema。"""
        tools = self._registry.list(enabled_only=enabled_only)
        schemas: list[dict[str, Any]] = []
        for t in tools:
            params = (
                t.args_schema.model_json_schema()  # type: ignore[union-attr]
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
