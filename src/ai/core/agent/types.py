"""Agent 类型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    """Agent 执行状态。"""

    SUCCESS = "success"
    MAX_ITERATIONS = "max_iterations"
    ERROR = "error"
    PLAN_MODE = "plan_mode"


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
class AgentResult:
    """Agent 执行结果。"""

    status: AgentStatus
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    iterations: int = 0
    total_tokens: int = 0
    plan: str | None = None

    @property
    def is_success(self) -> bool:
        """是否成功完成。"""
        return self.status == AgentStatus.SUCCESS

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
        }
