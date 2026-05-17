"""Graph 可观测性 — Token 计数、延迟追踪、调用统计。"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Optional

from src.ai_chat.config.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass
class GraphMetrics:
    """单次 Graph 执行的度量数据。"""

    graph_name: str
    model_name: str
    latency_ms: float
    success: bool
    input_tokens: int = 0
    output_tokens: int = 0
    execution_path: list[str] = field(default_factory=list)
    node_latencies: dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class GraphMetricsSummary:
    """度量汇总。"""

    total_calls: int = 0
    success_calls: int = 0
    failed_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0


class GraphMetricsCollector:
    """线程安全的 Graph 执行度量收集器。"""

    def __init__(self) -> None:
        self._metrics: list[GraphMetrics] = []
        self._lock = threading.Lock()

    def record(self, metrics: GraphMetrics) -> None:
        """记录一次执行度量。"""
        with self._lock:
            self._metrics.append(metrics)
        logger.debug(
            "Graph 度量: %s model=%s latency=%.0fms tokens=%d+%d path=%s",
            metrics.graph_name, metrics.model_name, metrics.latency_ms,
            metrics.input_tokens, metrics.output_tokens, metrics.execution_path,
        )

    def get_metrics(self, graph_name: str | None = None) -> list[GraphMetrics]:
        """获取度量记录，可按 graph 名称过滤。"""
        with self._lock:
            if graph_name:
                return [m for m in self._metrics if m.graph_name == graph_name]
            return list(self._metrics)

    def summary(self, graph_name: str | None = None) -> GraphMetricsSummary:
        """生成统计汇总。"""
        metrics = self.get_metrics(graph_name)
        if not metrics:
            return GraphMetricsSummary()

        total = len(metrics)
        success = sum(1 for m in metrics if m.success)
        total_in = sum(m.input_tokens for m in metrics)
        total_out = sum(m.output_tokens for m in metrics)
        total_latency = sum(m.latency_ms for m in metrics)

        return GraphMetricsSummary(
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
graph_metrics_collector = GraphMetricsCollector()
