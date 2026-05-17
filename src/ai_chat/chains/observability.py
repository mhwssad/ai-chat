"""Chain 可观测性 — Token 计数、延迟追踪、调用统计。"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional

from src.ai_chat.config.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass
class ChainMetrics:
    """单次 Chain 调用的度量数据。"""

    chain_name: str
    model_name: str
    latency_ms: float
    success: bool
    input_tokens: int = 0
    output_tokens: int = 0
    error: Optional[str] = None


@dataclass
class MetricsSummary:
    """度量汇总。"""

    total_calls: int = 0
    success_calls: int = 0
    failed_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0


class MetricsCollector:
    """线程安全的 Chain 调用度量收集器。"""

    def __init__(self) -> None:
        self._metrics: list[ChainMetrics] = []
        self._lock = threading.Lock()

    def record(self, metrics: ChainMetrics) -> None:
        """记录一次调用度量。"""
        with self._lock:
            self._metrics.append(metrics)
        logger.debug(
            "Chain 度量: %s model=%s latency=%.0fms tokens=%d+%d success=%s",
            metrics.chain_name, metrics.model_name, metrics.latency_ms,
            metrics.input_tokens, metrics.output_tokens, metrics.success,
        )

    def get_metrics(self, chain_name: str | None = None) -> list[ChainMetrics]:
        """获取度量记录，可按 chain 名称过滤。"""
        with self._lock:
            if chain_name:
                return [m for m in self._metrics if m.chain_name == chain_name]
            return list(self._metrics)

    def summary(self, chain_name: str | None = None) -> MetricsSummary:
        """生成统计汇总。"""
        metrics = self.get_metrics(chain_name)
        if not metrics:
            return MetricsSummary()

        total = len(metrics)
        success = sum(1 for m in metrics if m.success)
        total_in = sum(m.input_tokens for m in metrics)
        total_out = sum(m.output_tokens for m in metrics)
        total_latency = sum(m.latency_ms for m in metrics)

        return MetricsSummary(
            total_calls=total,
            success_calls=success,
            failed_calls=total - success,
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            total_latency_ms=total_latency,
            avg_latency_ms=total_latency / total if total else 0.0,
        )

    def reset(self) -> None:
        """清除所有度量记录。"""
        with self._lock:
            self._metrics.clear()

    def __len__(self) -> int:
        return len(self._metrics)


# 全局单例
metrics_collector = MetricsCollector()


def record_chain_call(
    chain_name: str,
    model_name: str,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> ChainMetrics:
    """记录 Chain 调用结果的上下文管理器辅助函数。

    用法::

        start = time.monotonic()
        try:
            result = chain.invoke(...)
            latency = (time.monotonic() - start) * 1000
            record_chain_call("chat", model_name, latency=latency)
        except Exception as e:
            ...
    """
    return ChainMetrics(
        chain_name=chain_name,
        model_name=model_name,
        latency_ms=0,
        success=True,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
