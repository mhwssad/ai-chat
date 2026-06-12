"""工具组合编排 — 将多个工具编排成 pipeline 或 workflow。

职责：
1. 定义 ToolPipeline：工具链声明（输入→转换→输出）
2. 支持常见组合模式：搜索→提取→总结、读取→分析→生成
3. Agent 可动态组合工具（由 LLM 决定组合方式）
4. 缓存中间结果，避免重复计算
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.ai.config.logging_setup import get_logger

logger = get_logger(__name__)


class PipelineStatus(str, Enum):
    """工具链执行状态。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # 部分步骤失败


@dataclass
class PipelineStep:
    """工具链中的单个步骤。

    Attributes:
        tool_name: 工具名称。
        arguments: 静态参数（不会被上游输出覆盖）。
        input_mapping: 输入映射：{本步骤参数名: 上游输出字段名}。
            特殊值 "$prev" 表示直接使用上一步的完整输出。
        output_key: 输出键名，用于后续步骤引用。
        condition: 执行条件（Python 表达式，可引用 "$prev" 和 "$context"）。
    """

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    input_mapping: dict[str, str] = field(default_factory=dict)
    output_key: str | None = None
    condition: str | None = None


@dataclass
class PipelineStepResult:
    """单步骤执行结果。"""

    step_index: int
    tool_name: str
    status: str  # success / failed / skipped
    output: Any = None
    error: str | None = None
    duration_ms: int = 0


@dataclass
class PipelineResult:
    """工具链执行结果。"""

    pipeline_name: str
    status: PipelineStatus
    steps: list[PipelineStepResult] = field(default_factory=list)
    final_output: Any = None
    context: dict[str, Any] = field(default_factory=dict)  # 各步骤的输出缓存
    total_duration_ms: int = 0


class ToolPipeline:
    """工具链编排 — 顺序执行多个工具，支持数据传递和缓存。

    常见组合模式：
    - 搜索→提取→总结
    - 读取→分析→生成
    - 查询→验证→格式化

    Args:
        name: 工具链名称。
        steps: 步骤列表。
        cache_enabled: 是否启用中间结果缓存。
    """

    def __init__(
        self,
        name: str,
        steps: list[PipelineStep],
        *,
        cache_enabled: bool = True,
    ) -> None:
        self._name = name
        self._steps = steps
        self._cache_enabled = cache_enabled
        self._cache: dict[str, Any] = {}

    @property
    def name(self) -> str:
        """工具链名称。"""
        return self._name

    @property
    def steps(self) -> list[PipelineStep]:
        """步骤列表。"""
        return list(self._steps)

    async def execute(
        self,
        initial_input: dict[str, Any] | None = None,
        *,
        execute_fn: Any | None = None,
    ) -> PipelineResult:
        """执行工具链。

        Args:
            initial_input: 初始输入（传递给第一个步骤）。
            execute_fn: 异步执行函数 (tool_name, arguments) -> result。
                如果为 None，结果仅为步骤描述。

        Returns:
            工具链执行结果。
        """
        import time

        start_time = time.perf_counter()
        results: list[PipelineStepResult] = []
        context: dict[str, Any] = dict(initial_input or {})
        prev_output: Any = None
        has_failure = False

        for i, step in enumerate(self._steps):
            # 检查缓存
            cache_key = self._make_cache_key(step, context) if self._cache_enabled else None
            if cache_key and cache_key in self._cache:
                logger.debug("工具链缓存命中: pipeline=%s, step=%d", self._name, i)
                cached = self._cache[cache_key]
                results.append(
                    PipelineStepResult(
                        step_index=i,
                        tool_name=step.tool_name,
                        status="success",
                        output=cached,
                        duration_ms=0,
                    )
                )
                if step.output_key:
                    context[step.output_key] = cached
                prev_output = cached
                continue

            # 检查执行条件
            if step.condition is not None:
                if not self._evaluate_condition(step.condition, prev_output, context):
                    results.append(
                        PipelineStepResult(
                            step_index=i,
                            tool_name=step.tool_name,
                            status="skipped",
                        )
                    )
                    continue

            # 构建步骤参数
            args = dict(step.arguments)
            for param_name, source_key in step.input_mapping.items():
                if source_key == "$prev" and prev_output is not None:
                    args[param_name] = prev_output
                elif source_key in context:
                    args[param_name] = context[source_key]

            # 执行
            step_start = time.perf_counter()
            try:
                if execute_fn is not None:
                    output = await execute_fn(step.tool_name, args)
                else:
                    output = f"[模拟执行] {step.tool_name}({args})"

                duration = int((time.perf_counter() - step_start) * 1000)
                results.append(
                    PipelineStepResult(
                        step_index=i,
                        tool_name=step.tool_name,
                        status="success",
                        output=output,
                        duration_ms=duration,
                    )
                )

                # 缓存结果
                if cache_key:
                    self._cache[cache_key] = output

                if step.output_key:
                    context[step.output_key] = output
                prev_output = output

            except Exception as e:
                duration = int((time.perf_counter() - step_start) * 1000)
                results.append(
                    PipelineStepResult(
                        step_index=i,
                        tool_name=step.tool_name,
                        status="failed",
                        error=str(e),
                        duration_ms=duration,
                    )
                )
                has_failure = True
                prev_output = None
                logger.warning(
                    "工具链步骤失败: pipeline=%s, step=%d, tool=%s, error=%s",
                    self._name,
                    i,
                    step.tool_name,
                    str(e)[:200],
                )

        total_duration = int((time.perf_counter() - start_time) * 1000)

        # 确定最终状态
        if has_failure:
            success_count = sum(1 for r in results if r.status == "success")
            status = PipelineStatus.PARTIAL if success_count > 0 else PipelineStatus.FAILED
        else:
            status = PipelineStatus.COMPLETED

        return PipelineResult(
            pipeline_name=self._name,
            status=status,
            steps=results,
            final_output=prev_output,
            context=context,
            total_duration_ms=total_duration,
        )

    def clear_cache(self) -> None:
        """清空缓存。"""
        self._cache.clear()

    @staticmethod
    def _make_cache_key(step: PipelineStep, context: dict[str, Any]) -> str:
        """生成步骤缓存键。"""
        key_data = {
            "tool": step.tool_name,
            "args": step.arguments,
            "mapping": step.input_mapping,
        }
        raw = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _evaluate_condition(condition: str, prev_output: Any, context: dict[str, Any]) -> bool:
        """评估执行条件。

        支持简单的条件表达式，可引用 $prev 和 $context。
        """
        try:
            eval_context = {"$prev": prev_output, "$context": context}
            # 仅允许安全的名称访问
            return bool(eval(condition, {"__builtins__": {}}, eval_context))  # noqa: S307
        except Exception:
            logger.warning("条件评估失败: condition=%s", condition)
            return True  # 评估失败时默认执行


# ── 预置常用工具链模式 ──────────────────────────────────────


def create_search_extract_summarize_pipeline() -> ToolPipeline:
    """搜索→提取→总结 工具链。"""
    return ToolPipeline(
        name="search_extract_summarize",
        steps=[
            PipelineStep(
                tool_name="web_search",
                arguments={},
                input_mapping={"query": "query"},
                output_key="search_results",
            ),
            PipelineStep(
                tool_name="read_file",
                arguments={},
                input_mapping={"path": "$prev"},
                output_key="extracted_content",
            ),
            PipelineStep(
                tool_name="web_search",
                arguments={"query": "请总结以下内容"},
                input_mapping={"query": "$prev"},
                output_key="summary",
            ),
        ],
    )


def create_read_analyze_generate_pipeline() -> ToolPipeline:
    """读取→分析→生成 工具链。"""
    return ToolPipeline(
        name="read_analyze_generate",
        steps=[
            PipelineStep(
                tool_name="read_file",
                arguments={},
                input_mapping={"path": "file_path"},
                output_key="file_content",
            ),
            PipelineStep(
                tool_name="shell_command",
                arguments={},
                input_mapping={"command": "$prev"},
                output_key="analysis_result",
                condition="$prev is not None",
            ),
        ],
    )
