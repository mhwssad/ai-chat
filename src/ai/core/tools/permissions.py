"""工具权限控制 — 将权限标签从元数据升级为实际校验机制。"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Literal

if TYPE_CHECKING:
    from src.ai.core.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# 确认回调类型：接收工具名和参数，返回是否允许执行
ConfirmHandler = Callable[[str, dict[str, Any]], Awaitable[bool]]

# 缓存 TTL（秒）— 5 分钟后需要重新确认
_CACHE_TTL_SECONDS = 300


class PermissionLevel(Enum):
    """权限级别。"""

    AUTO = "auto"  # 自动放行
    CONFIRM = "confirm"  # 需要用户确认
    DENY = "deny"  # 拒绝执行


PermissionDecisionValue = Literal["allow", "ask", "deny"]


@dataclass(frozen=True)
class PermissionDecision:
    """工具权限决策结果。"""

    decision: PermissionDecisionValue
    tool_name: str
    permissions: list[str] = field(default_factory=list)
    reason: str = ""
    confirmed: bool | None = None
    cached: bool = False
    context: dict[str, Any] = field(default_factory=dict)


# 默认权限策略：权限标签 → 权限级别
DEFAULT_POLICY: dict[str, PermissionLevel] = {
    "file_read": PermissionLevel.AUTO,
    "file_write": PermissionLevel.CONFIRM,
    "command_exec": PermissionLevel.CONFIRM,
    "external_service": PermissionLevel.AUTO,
}


def _make_cache_key(tool_name: str, arguments: dict[str, Any]) -> str:
    """生成缓存键：工具名 + 参数哈希。"""
    args_str = json.dumps(arguments, sort_keys=True, default=str)
    args_hash = hashlib.sha256(args_str.encode()).hexdigest()[:16]
    return f"{tool_name}:{args_hash}"


class PermissionChecker:
    """权限校验器。

    根据工具的权限标签和策略映射决定是否允许执行。
    对于 CONFIRM 级别的工具，通过 confirm_handler 回调请求用户确认。

    缓存策略：
    - 按工具名 + 参数哈希缓存确认结果
    - TTL 5 分钟，过期后需要重新确认

    Args:
        registry: 工具注册表。
        policy: 权限策略映射（覆盖默认策略）。
    """

    def __init__(
        self,
        registry: ToolRegistry,
        *,
        policy: dict[str, PermissionLevel] | None = None,
    ) -> None:
        self._registry = registry
        self._policy = {**DEFAULT_POLICY, **(policy or {})}
        self._confirm_handler: ConfirmHandler | None = None
        # 缓存已确认的工具：{cache_key: expire_time}
        self._confirmed_cache: dict[str, float] = {}

    def set_confirm_handler(self, handler: ConfirmHandler | None) -> None:
        """设置确认回调。UI 层通过此方法注册用户确认逻辑。

        Args:
            handler: 确认回调函数，None 表示清除。
        """
        self._confirm_handler = handler

    def clear_cache(self) -> None:
        """清空已确认缓存。"""
        self._confirmed_cache.clear()

    def _cleanup_expired(self) -> None:
        """清理过期的缓存条目。"""
        now = time.monotonic()
        expired_keys = [k for k, v in self._confirmed_cache.items() if v < now]
        for key in expired_keys:
            del self._confirmed_cache[key]

    async def check(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """校验工具是否允许执行。

        Args:
            tool_name: 工具名称。
            arguments: 工具参数。

        Returns:
            True 表示允许执行，False 表示拒绝。

        Raises:
            ToolPermissionError: 当权限被拒绝时。
        """
        decision = await self.decide(tool_name, arguments)
        if decision.decision == "allow":
            return True
        self._raise_for_decision(decision)
        return False

    async def decide(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> PermissionDecision:
        """返回结构化权限决策结果。"""
        meta = self._registry.get_meta(tool_name)
        permissions = meta.permissions

        # 无权限标签的工具自动放行
        if not permissions:
            return PermissionDecision(
                decision="allow",
                tool_name=tool_name,
                permissions=[],
                reason="no_permissions_required",
            )

        # 确定最高权限级别
        level = self._resolve_level(permissions)

        if level == PermissionLevel.AUTO:
            return PermissionDecision(
                decision="allow",
                tool_name=tool_name,
                permissions=permissions,
                reason="policy_auto",
            )

        if level == PermissionLevel.DENY:
            logger.warning("工具 %s 被权限策略拒绝", tool_name)
            return PermissionDecision(
                decision="deny",
                tool_name=tool_name,
                permissions=permissions,
                reason="policy_deny",
            )

        # CONFIRM 级别：检查缓存或调用确认回调
        cache_key = _make_cache_key(tool_name, arguments)
        now = time.monotonic()

        # 检查缓存（带 TTL）
        if cache_key in self._confirmed_cache:
            expire_time = self._confirmed_cache[cache_key]
            if now < expire_time:
                return PermissionDecision(
                    decision="allow",
                    tool_name=tool_name,
                    permissions=permissions,
                    reason="cached_confirmation",
                    confirmed=True,
                    cached=True,
                )
            # 过期，删除
            del self._confirmed_cache[cache_key]

        # 定期清理过期缓存
        self._cleanup_expired()

        if self._confirm_handler is None:
            # 无确认回调时默认拒绝（安全优先）
            logger.warning("工具 %s 需要确认但无 confirm_handler，默认拒绝", tool_name)
            return PermissionDecision(
                decision="ask",
                tool_name=tool_name,
                permissions=permissions,
                reason="confirm_handler_missing",
                confirmed=None,
            )

        try:
            confirmed = await self._confirm_handler(tool_name, arguments)
        except Exception:
            logger.exception("确认回调执行异常: tool=%s", tool_name)
            return PermissionDecision(
                decision="deny",
                tool_name=tool_name,
                permissions=permissions,
                reason="confirm_handler_error",
                confirmed=False,
            )

        if confirmed:
            self._confirmed_cache[cache_key] = now + _CACHE_TTL_SECONDS
            return PermissionDecision(
                decision="allow",
                tool_name=tool_name,
                permissions=permissions,
                reason="user_confirmed",
                confirmed=True,
            )

        return PermissionDecision(
            decision="deny",
            tool_name=tool_name,
            permissions=permissions,
            reason="user_denied",
            confirmed=False,
        )

    def _resolve_level(self, permissions: list[str]) -> PermissionLevel:
        """根据权限标签列表确定最高权限级别。

        优先级：DENY > CONFIRM > AUTO。

        Args:
            permissions: 权限标签列表。

        Returns:
            最高权限级别。
        """
        result = PermissionLevel.AUTO
        for perm in permissions:
            level = self._policy.get(perm, PermissionLevel.AUTO)
            if level == PermissionLevel.DENY:
                return PermissionLevel.DENY
            if level == PermissionLevel.CONFIRM:
                result = PermissionLevel.CONFIRM
        return result

    @staticmethod
    def _raise_for_decision(decision: PermissionDecision) -> None:
        """将结构化决策转换为兼容旧调用的异常。"""
        from src.ai.exception.tool_exception import (
            ToolConfirmationRequiredError,
            ToolPermissionError,
        )

        message = "工具执行被拒绝"
        if decision.decision == "ask":
            message = "需要用户确认但无确认回调"
            raise ToolConfirmationRequiredError(
                message,
                context={
                    "tool": decision.tool_name,
                    "permissions": decision.permissions,
                    "decision": decision.decision,
                    "reason": decision.reason,
                },
            )
        elif decision.reason == "user_denied":
            message = "用户拒绝执行工具"
        elif decision.reason == "confirm_handler_error":
            message = "权限确认过程异常"
        raise ToolPermissionError(
            message,
            context={
                "tool": decision.tool_name,
                "permissions": decision.permissions,
                "decision": decision.decision,
                "reason": decision.reason,
            },
        )
