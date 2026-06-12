"""工具错误恢复策略 — 失败时自动重试、换工具、重新规划或询问用户。

职责：
1. 根据错误类型选择合适的恢复策略
2. 支持重试（相同工具+参数）、回退（换工具）、重新规划、询问用户
3. 记录恢复事件到审计日志
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.ai.config.logging_setup import get_logger

logger = get_logger(__name__)


class RecoveryStrategy(str, Enum):
    """错误恢复策略。"""

    RETRY = "retry"  # 使用相同工具和参数重试
    FALLBACK = "fallback"  # 换用备选工具
    REPLAN = "replan"  # 将错误信息反馈给 LLM 重新规划
    ASK_USER = "ask_user"  # 询问用户如何处理


@dataclass
class RecoveryEvent:
    """单次恢复事件记录。"""

    tool_name: str
    strategy: RecoveryStrategy
    attempt: int  # 第几次恢复尝试
    error_message: str  # 原始错误消息
    action_taken: str  # 采取的具体行动描述
    success: bool = False  # 恢复是否成功


@dataclass
class RecoveryConfig:
    """恢复策略配置。

    Attributes:
        max_retries: 最大重试次数（默认 2）。
        retry_delay_base: 重试基础延迟（秒），指数退避。
        fallback_map: 工具名 → 备选工具名的映射。
        strategy_rules: 错误模式 → 策略的映射规则。
    """

    max_retries: int = 2
    retry_delay_base: float = 1.0
    fallback_map: dict[str, str] = field(default_factory=dict)
    strategy_rules: dict[str, RecoveryStrategy] = field(default_factory=lambda: {
        "timeout": RecoveryStrategy.RETRY,
        "connection": RecoveryStrategy.RETRY,
        "not_found": RecoveryStrategy.FALLBACK,
        "permission": RecoveryStrategy.ASK_USER,
        "rate_limit": RecoveryStrategy.RETRY,
        "default": RecoveryStrategy.REPLAN,
    })

    def get_strategy(self, error: Exception | str) -> RecoveryStrategy:
        """根据错误类型选择恢复策略。

        Args:
            error: 异常对象或错误消息字符串。

        Returns:
            推荐的恢复策略。
        """
        error_msg = str(error).lower()
        error_type = type(error).__name__.lower() if isinstance(error, Exception) else ""

        # 匹配错误消息关键词
        for pattern, strategy in self.strategy_rules.items():
            if pattern == "default":
                continue
            if pattern in error_msg or pattern in error_type:
                return strategy

        # 返回默认策略
        return self.strategy_rules.get("default", RecoveryStrategy.REPLAN)


class RecoveryManager:
    """错误恢复管理器 — 根据错误类型执行恢复策略。

    在工具执行失败时，根据配置的策略尝试恢复：
    - RETRY: 延迟后使用相同参数重试
    - FALLBACK: 查找备选工具执行
    - REPLAN: 返回错误消息让 LLM 重新规划
    - ASK_USER: 标记需要用户介入

    Args:
        config: 恢复策略配置。
        tool_registry: 工具注册表（用于查找备选工具）。
    """

    def __init__(
        self,
        *,
        config: RecoveryConfig | None = None,
        tool_registry: Any | None = None,
    ) -> None:
        self._config = config or RecoveryConfig()
        self._registry = tool_registry
        self._history: list[RecoveryEvent] = []

    @property
    def history(self) -> list[RecoveryEvent]:
        """获取恢复历史记录。"""
        return list(self._history)

    @property
    def config(self) -> RecoveryConfig:
        """获取当前配置。"""
        return self._config

    def decide_strategy(
        self,
        tool_name: str,
        error: Exception | str,
        attempt: int,
    ) -> RecoveryStrategy:
        """决定恢复策略。

        Args:
            tool_name: 失败的工具名称。
            error: 错误对象或消息。
            attempt: 当前是第几次尝试。

        Returns:
            恢复策略。
        """
        # 超过最大重试次数，直接重新规划或询问用户
        if attempt >= self._config.max_retries:
            return RecoveryStrategy.REPLAN

        # 检查是否有 fallback 工具
        if tool_name in self._config.fallback_map:
            fallback = self._config.fallback_map[tool_name]
            if self._registry is not None:
                try:
                    self._registry.get(fallback)
                    # fallback 工具存在，仅在非首次失败时使用
                    if attempt >= 1:
                        return RecoveryStrategy.FALLBACK
                except Exception:
                    pass  # fallback 工具不存在，继续

        # 根据错误类型选择策略
        return self._config.get_strategy(error)

    async def execute_recovery(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        error: Exception | str,
        attempt: int,
        execute_fn: Any | None = None,
    ) -> dict[str, Any]:
        """执行恢复策略。

        Args:
            tool_name: 失败的工具名称。
            arguments: 原始调用参数。
            error: 错误对象或消息。
            attempt: 当前尝试次数。
            execute_fn: 异步执行函数（tool_name, arguments）-> result。

        Returns:
            恢复结果字典，包含 action 和可能的 result/error。
        """
        import asyncio

        strategy = self.decide_strategy(tool_name, error, attempt)
        error_msg = str(error)

        logger.info(
            "工具恢复: tool=%s, strategy=%s, attempt=%d, error=%s",
            tool_name,
            strategy.value,
            attempt,
            error_msg[:200],
        )

        if strategy == RecoveryStrategy.RETRY and execute_fn is not None:
            # 指数退避延迟
            delay = self._config.retry_delay_base * (2 ** attempt)
            await asyncio.sleep(delay)

            try:
                result = await execute_fn(tool_name, arguments)
                event = RecoveryEvent(
                    tool_name=tool_name,
                    strategy=strategy,
                    attempt=attempt,
                    error_message=error_msg,
                    action_taken=f"延迟 {delay:.1f}s 后重试成功",
                    success=True,
                )
                self._history.append(event)
                return {"action": "retry", "result": result}
            except Exception as retry_error:
                event = RecoveryEvent(
                    tool_name=tool_name,
                    strategy=strategy,
                    attempt=attempt,
                    error_message=error_msg,
                    action_taken=f"重试失败: {retry_error}",
                    success=False,
                )
                self._history.append(event)
                return {"action": "retry_failed", "error": str(retry_error)}

        elif strategy == RecoveryStrategy.FALLBACK and execute_fn is not None:
            fallback_name = self._config.fallback_map.get(tool_name, "")
            if fallback_name:
                try:
                    result = await execute_fn(fallback_name, arguments)
                    event = RecoveryEvent(
                        tool_name=tool_name,
                        strategy=strategy,
                        attempt=attempt,
                        error_message=error_msg,
                        action_taken=f"回退到备选工具 {fallback_name} 成功",
                        success=True,
                    )
                    self._history.append(event)
                    return {
                        "action": "fallback",
                        "fallback_tool": fallback_name,
                        "result": result,
                    }
                except Exception as fb_error:
                    event = RecoveryEvent(
                        tool_name=tool_name,
                        strategy=strategy,
                        attempt=attempt,
                        error_message=error_msg,
                        action_taken=f"备选工具 {fallback_name} 也失败: {fb_error}",
                        success=False,
                    )
                    self._history.append(event)
                    return {"action": "fallback_failed", "error": str(fb_error)}

        elif strategy == RecoveryStrategy.ASK_USER:
            event = RecoveryEvent(
                tool_name=tool_name,
                strategy=strategy,
                attempt=attempt,
                error_message=error_msg,
                action_taken="标记需要用户介入",
                success=False,
            )
            self._history.append(event)
            return {
                "action": "ask_user",
                "message": f"工具 {tool_name} 执行失败: {error_msg}。请提供指导。",
            }

        # REPLAN: 返回错误消息让 LLM 重新规划
        event = RecoveryEvent(
            tool_name=tool_name,
            strategy=strategy,
            attempt=attempt,
            error_message=error_msg,
            action_taken="将错误反馈给 LLM 重新规划",
            success=False,
        )
        self._history.append(event)
        return {
            "action": "replan",
            "message": (
                f"工具 {tool_name} 执行失败（已尝试 {attempt + 1} 次）: {error_msg}。"
                f"请尝试其他方法完成任务。"
            ),
        }
