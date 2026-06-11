"""统一工具服务 — 工具查询、启用/禁用、测试执行。

共享服务层，CLI 命令、CLI 标签页和 API 路由统一使用。
"""

from __future__ import annotations

import json
from src.ai.config.logging_setup import get_logger
import time
from typing import Any

from src.ai.core.callbacks.audit import AuditEvent, record_audit_event
from src.ai.core.tools.types import ToolDescriptor, ToolExecutionDiagnostic
from src.ai.storage import ToolCallRepository
from src.ai.storage.database import get_session
from src.ai.utils.redaction import redact_for_audit

logger = get_logger(__name__)


class ToolService:
    """统一工具服务。

    职责：
    1. 工具列表查询（含元数据和 schema）
    2. 工具启用/禁用
    3. 工具测试执行
    4. 工具搜索
    """

    def __init__(
        self,
        *,
        tool_registry: Any,
        tool_manager: Any,
    ) -> None:
        self._registry = tool_registry
        self._manager = tool_manager

    # ── 查询 ──────────────────────────────────────────────────

    def list_tools(
        self,
        *,
        enabled_only: bool = True,
    ) -> list[dict[str, Any]]:
        """列出工具（含元数据）。

        Args:
            enabled_only: 是否只返回启用的工具。

        Returns:
            工具信息列表。
        """
        return [
            self._descriptor_to_dict(item)
            for item in self._registry.list_descriptors(enabled_only=enabled_only)
        ]

    def list_schemas(
        self,
        *,
        enabled_only: bool = True,
    ) -> list[dict[str, Any]]:
        """列出 OpenAI function-calling schema。

        Args:
            enabled_only: 是否只返回启用的工具。

        Returns:
            工具 schema 列表。
        """
        return self._manager.list_schemas(enabled_only=enabled_only)

    def get_tool_detail(self, name: str) -> dict[str, Any]:
        """获取工具详情（元数据 + 参数 schema）。

        Args:
            name: 工具名称。

        Returns:
            工具详情字典。

        Raises:
            KeyError: 工具不存在。
        """
        tool = self._registry.get(name)
        descriptor = self._registry.get_descriptor(name)

        # 获取参数 schema
        schema_dict: dict[str, Any] = {}
        args_schema = tool.args_schema
        if args_schema:
            schema_dict = (
                args_schema.model_json_schema()
                if hasattr(args_schema, "model_json_schema")
                else {}
            )

        return {
            **self._descriptor_to_dict(descriptor),
            "args_schema": schema_dict,
            "input_schema": schema_dict,
        }

    def search_tools(
        self,
        query: str,
        *,
        enabled_only: bool = True,
    ) -> list[dict[str, Any]]:
        """按关键词搜索工具（匹配名称或描述）。

        Args:
            query: 搜索关键词。
            enabled_only: 是否只搜索启用的工具。

        Returns:
            匹配的工具列表。
        """
        all_tools = self.list_tools(enabled_only=enabled_only)
        query_lower = query.lower()
        return [
            t
            for t in all_tools
            if query_lower in t["name"].lower()
            or query_lower in t["description"].lower()
        ]

    # ── 启用/禁用 ────────────────────────────────────────────

    def enable_tool(self, name: str) -> None:
        """启用工具。

        Args:
            name: 工具名称。

        Raises:
            KeyError: 工具不存在。
        """
        meta = self._registry.get_meta(name)
        meta.enabled = True

    def disable_tool(self, name: str) -> None:
        """禁用工具（核心工具不可禁用）。

        Args:
            name: 工具名称。

        Raises:
            KeyError: 工具不存在。
            ValueError: 尝试禁用核心工具。
        """
        meta = self._registry.get_meta(name)
        if meta.essential:
            raise ValueError(f"不能禁用核心工具: {name}")
        meta.enabled = False

    # ── 测试执行 ──────────────────────────────────────────────

    async def execute_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> Any:
        """测试执行工具。

        Args:
            name: 工具名称。
            arguments: 工具参数。
            timeout: 超时秒数。

        Returns:
            工具执行结果。
        """
        return await self._manager.execute(name, arguments or {})

    async def execute_tool_diagnostic(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        session_id: str | None = None,
    ) -> ToolExecutionDiagnostic:
        """执行工具并返回诊断信息。"""
        args = arguments or {}
        descriptor = self._registry.get_descriptor(name)
        input_summary = self._summary(args)
        started = time.perf_counter()
        permission = await self.check_permission(name, args)
        permission_decision = (
            permission["decision"] if permission is not None else "allow"
        )

        if permission_decision != "allow":
            diagnostic = ToolExecutionDiagnostic(
                tool_name=name,
                source_type=descriptor.source_type,
                source_id=descriptor.source_id,
                status="denied",
                duration_ms=self._duration_ms(started),
                permission_decision=permission_decision,
                input_summary=input_summary,
                error_type="ToolPermissionError",
                error_message=redact_for_audit(
                    permission.get("reason", "permission_denied")
                    if permission is not None
                    else "permission_denied"
                ),
            )
            self._record_diagnostic(diagnostic, session_id=session_id)
            return diagnostic

        try:
            result = await self._manager.execute(
                name,
                args,
                timeout=timeout,
            )
            diagnostic = ToolExecutionDiagnostic(
                tool_name=name,
                source_type=descriptor.source_type,
                source_id=descriptor.source_id,
                status="success",
                duration_ms=self._duration_ms(started),
                permission_decision=permission_decision,
                input_summary=input_summary,
                output_summary=self._summary(result),
                result=result,
            )
            self._record_diagnostic(diagnostic, session_id=session_id)
            return diagnostic
        except Exception as exc:
            status = (
                "timeout"
                if type(exc).__name__ == "ToolExecutionError" and "超时" in str(exc)
                else "failed"
            )
            diagnostic = ToolExecutionDiagnostic(
                tool_name=name,
                source_type=descriptor.source_type,
                source_id=descriptor.source_id,
                status=status,
                duration_ms=self._duration_ms(started),
                permission_decision=permission_decision,
                input_summary=input_summary,
                error_type=type(exc).__name__,
                error_message=redact_for_audit(str(exc)),
            )
            self._record_diagnostic(diagnostic, session_id=session_id)
            return diagnostic

    async def check_permission(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """检查工具权限并返回结构化决策。"""
        decision = await self._manager.check_permission(name, arguments or {})
        if decision is None:
            return None
        return {
            "decision": decision.decision,
            "tool_name": decision.tool_name,
            "permissions": decision.permissions,
            "reason": decision.reason,
            "confirmed": decision.confirmed,
            "cached": decision.cached,
            "context": decision.context,
        }

    @staticmethod
    def _descriptor_to_dict(descriptor: ToolDescriptor) -> dict[str, Any]:
        """将统一描述对象转换为 API/TUI 共用字典。"""
        return {
            "name": descriptor.name,
            "display_name": descriptor.display_name,
            "description": descriptor.description,
            "source_type": descriptor.source_type,
            "source_id": descriptor.source_id,
            "permissions": descriptor.permissions,
            "output_description": descriptor.output_description,
            "essential": descriptor.essential,
            "enabled": descriptor.enabled,
        }

    @staticmethod
    def _duration_ms(started: float) -> int:
        """计算耗时毫秒。"""
        return int((time.perf_counter() - started) * 1000)

    @staticmethod
    def _summary(value: Any, *, max_length: int = 500) -> str:
        """生成可审计的脱敏摘要。"""
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except TypeError:
            text = str(value)
        return redact_for_audit(text, max_length=max_length)

    def _record_diagnostic(
        self,
        diagnostic: ToolExecutionDiagnostic,
        *,
        session_id: str | None = None,
    ) -> None:
        """写入工具执行记录和审计日志。"""
        try:
            with get_session() as session:
                ToolCallRepository(session).create(
                    session_id=session_id,
                    tool_name=diagnostic.tool_name,
                    source_type=diagnostic.source_type,
                    source_id=diagnostic.source_id,
                    input_summary=diagnostic.input_summary,
                    output_summary=diagnostic.output_summary,
                    duration_ms=diagnostic.duration_ms,
                    status=diagnostic.status,
                    error_type=diagnostic.error_type,
                    error_message=diagnostic.error_message,
                )
            record_audit_event(
                AuditEvent(
                    session_id=session_id,
                    event_type="tool_call",
                    source_module="tools",
                    target=diagnostic.tool_name,
                    input_summary=diagnostic.input_summary,
                    output_summary=diagnostic.output_summary,
                    status="denied"
                    if diagnostic.status == "denied"
                    else ("success" if diagnostic.status == "success" else "failed"),
                    duration_ms=diagnostic.duration_ms,
                    permission_decision=diagnostic.permission_decision,
                    error_type=diagnostic.error_type,
                    error_message=diagnostic.error_message,
                    metadata={
                        "source_type": diagnostic.source_type,
                        "source_id": diagnostic.source_id,
                    },
                )
            )
        except Exception:
            logger.debug(
                "工具诊断记录写入失败: %s", diagnostic.tool_name, exc_info=True
            )
