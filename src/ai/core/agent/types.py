"""Agent 类型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    """Agent 执行状态。"""

    SUCCESS = "success"
    MAX_ITERATIONS = "max_iterations"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    WAITING_CONFIRMATION = "waiting_confirmation"
    PLAN_MODE = "plan_mode"

    # 兼容旧调用方；新代码应使用 FAILED。
    ERROR = "failed"


@dataclass
class ToolCall:
    """工具调用记录。"""

    id: str
    name: str
    arguments: dict[str, Any]
    result: str | None = None
    error: str | None = None
    duration_ms: int = 0


@dataclass
class AgentTraceStep:
    """Agent 执行轨迹步骤。"""

    index: int
    step_type: str
    title: str
    summary: str
    status: str = "success"
    error: str | None = None


@dataclass
class AgentResult:
    """Agent 执行结果。"""

    status: AgentStatus
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    iterations: int = 0
    total_tokens: int = 0
    plan: str | None = None
    trace: list[AgentTraceStep] = field(default_factory=list)
    context_sources: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        """是否成功完成。"""
        return self.status == AgentStatus.SUCCESS

    @property
    def is_terminal_failure(self) -> bool:
        """是否为终止性失败状态。"""
        return self.status in {
            AgentStatus.FAILED,
            AgentStatus.TIMEOUT,
            AgentStatus.CANCELLED,
            AgentStatus.MAX_ITERATIONS,
        }

    @property
    def has_tool_calls(self) -> bool:
        """是否有工具调用。"""
        return len(self.tool_calls) > 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "status": self.status.value,
            "content": self.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "result": tc.result,
                    "error": tc.error,
                    "duration_ms": tc.duration_ms,
                }
                for tc in self.tool_calls
            ],
            "iterations": self.iterations,
            "total_tokens": self.total_tokens,
            "plan": self.plan,
            "trace": [
                {
                    "index": step.index,
                    "step_type": step.step_type,
                    "title": step.title,
                    "summary": step.summary,
                    "status": step.status,
                    "error": step.error,
                }
                for step in self.trace
            ],
            "context_sources": self.context_sources,
        }
