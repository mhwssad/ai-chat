"""弹性策略模块 — 重试、熔断器与可观测性工具。

为 LLM 调用提供统一的弹性保护，包括指数退避重试和按供应商隔离的熔断器。
所有弹性策略集中在 Factory 层应用，Provider 子类无需任何修改。

用法::

    from src.ai_chat.llm.resilience import create_retry_decorator, get_circuit_breaker

    cb = get_circuit_breaker("openai")
    retry_fn = create_retry_decorator("openai", "gpt-4o")

    @retry_fn
    def _invoke():
        return provider.chat(request, model_name)

    return cb.call(_invoke)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

import httpx
import pybreaker
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.models import LLMCircuitOpenError

logger = get_logger(__name__)

F = TypeVar("F")

# 重试时捕获的异常类型 — 网络/超时相关
_RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.NetworkError,
)


@dataclass
class ResilienceConfig:
    """弹性策略配置。

    Attributes:
        retry_max_attempts: 最大重试次数（含首次调用）
        retry_min_wait: 退避最小等待时间（秒）
        retry_max_wait: 退避最大等待时间（秒）
        circuit_fail_max: 熔断器打开前的连续失败次数
        circuit_reset_timeout: 熔断器打开后到半开的等待时间（秒）
    """

    retry_max_attempts: int = 3
    retry_min_wait: float = 1.0
    retry_max_wait: float = 10.0
    circuit_fail_max: int = 5
    circuit_reset_timeout: float = 60.0


# 模块级默认配置
_default_config = ResilienceConfig()


def create_retry_decorator(
    provider_name: str = "",
    model_name: str = "",
    config: ResilienceConfig | None = None,
) -> Callable[[F], F]:
    """创建重试装饰器。

    Args:
        provider_name: 供应商名称，用于日志
        model_name: 模型名称，用于日志
        config: 弹性策略配置，None 时使用默认值

    Returns:
        tenacity 重试装饰器
    """
    cfg = config or _default_config

    def _before_sleep(retry_state) -> None:
        """每次重试前的日志回调。"""
        logger.warning(
            "[%s] LLM 调用重试 (%d/%d): model=%s, 等待=%.1fs, 异常=%s",
            provider_name,
            retry_state.attempt_number,
            cfg.retry_max_attempts,
            model_name,
            retry_state.next_action.sleep if retry_state.next_action else 0,
            retry_state.outcome.exception() if retry_state.outcome else "unknown",
        )

    return retry(
        stop=stop_after_attempt(cfg.retry_max_attempts),
        wait=wait_exponential(
            multiplier=1, min=cfg.retry_min_wait, max=cfg.retry_max_wait
        ),
        retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
        before_sleep=_before_sleep,
        reraise=True,
    )


class CircuitBreakerRegistry:
    """按供应商名称管理独立的熔断器实例。

    每个供应商拥有独立的熔断器，某个 API 故障不会影响其他供应商的路由。
    """

    def __init__(self, config: ResilienceConfig | None = None) -> None:
        self._config = config or _default_config
        self._breakers: dict[str, pybreaker.CircuitBreaker] = {}

    def get_breaker(
        self, provider_name: str, model_name: str = ""
    ) -> pybreaker.CircuitBreaker:
        """获取指定供应商的熔断器，不存在时自动创建。

        Args:
            provider_name: 供应商名称
            model_name: 模型名称，非空时按 (provider, model) 维度隔离

        Returns:
            该维度的 CircuitBreaker 实例
        """
        key = f"{provider_name}:{model_name}" if model_name else provider_name
        if key not in self._breakers:
            self._breakers[key] = pybreaker.CircuitBreaker(
                fail_max=self._config.circuit_fail_max,
                reset_timeout=self._config.circuit_reset_timeout,
                name=f"llm-{key}",
            )
            logger.debug(
                "创建熔断器: key='%s', fail_max=%d, reset_timeout=%.0fs",
                key,
                self._config.circuit_fail_max,
                self._config.circuit_reset_timeout,
            )
        return self._breakers[key]

    def reset_all(self) -> None:
        """重置所有熔断器到关闭状态。"""
        for name, breaker in self._breakers.items():
            breaker.close()
            logger.info("已重置熔断器: provider='%s'", name)


# 模块级单例
_circuit_registry = CircuitBreakerRegistry()


def get_circuit_breaker(provider_name: str) -> pybreaker.CircuitBreaker:
    """获取指定供应商的熔断器。"""
    return _circuit_registry.get_breaker(provider_name)


def wrap_with_resilience(
    provider_name: str,
    model_name: str,
    fn: Callable[[], object],
    *,
    use_circuit_breaker: bool = True,
    config: ResilienceConfig | None = None,
) -> object:
    """统一弹性策略包装 — 重试 + 熔断 + 耗时日志。

    Args:
        provider_name: 供应商名称
        model_name: 模型名称
        fn: 无参可调用对象，执行实际的 LLM 调用
        use_circuit_breaker: 是否启用熔断（stream 场景应设为 False）
        config: 弹性策略配置

    Returns:
        fn 的返回值

    Raises:
        LLMCircuitOpenError: 熔断器已开启
        LLMRetryExhaustedError: 重试耗尽后仍失败
    """
    cfg = config or _default_config
    retry_decorator = create_retry_decorator(provider_name, model_name, cfg)

    @retry_decorator
    def _invoke():
        return fn()

    if use_circuit_breaker:
        cb = get_circuit_breaker(provider_name, model_name)
        try:
            return cb.call(_invoke)
        except pybreaker.CircuitBreakerError as e:
            raise LLMCircuitOpenError(
                f"熔断器已开启，供应商 '{provider_name}' 暂时不可用",
                context={"provider": provider_name, "model": model_name},
                error_code="CIRCUIT_OPEN",
            ) from e
    else:
        return _invoke()
