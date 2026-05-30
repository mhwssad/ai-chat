"""定时任务数据类型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    """任务状态枚举。"""

    ACTIVE = "active"  # 活跃状态，等待执行
    PAUSED = "paused"  # 暂停状态
    COMPLETED = "completed"  # 已完成（一次性任务）
    FAILED = "failed"  # 失败状态（超过最大重试次数）
    DISABLED = "disabled"  # 已禁用


class TaskType(str, Enum):
    """任务类型枚举。"""

    TOOL_CALL = "tool_call"  # 调用工具
    LLM_PROMPT = "llm_prompt"  # 执行 LLM 提示
    SYSTEM_EVENT = "system_event"  # 系统事件


class ExecutionStatus(str, Enum):
    """执行状态枚举。"""

    RUNNING = "running"  # 运行中
    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失败
    TIMEOUT = "timeout"  # 超时
    CANCELLED = "cancelled"  # 已取消


@dataclass
class CronSpec:
    """Cron 表达式规范。

    支持标准 5 位 Cron 表达式：分 时 日 月 周
    也支持间隔模式：interval_seconds
    """

    cron_expr: str | None = None
    interval_seconds: int | None = None
    one_shot: bool = False

    def validate(self) -> bool:
        """验证 Cron 配置是否有效。"""
        if self.cron_expr and self.interval_seconds:
            return False  # 不能同时指定
        if not self.cron_expr and not self.interval_seconds and not self.one_shot:
            return False  # 至少指定一种
        if self.cron_expr:
            parts = self.cron_expr.strip().split()
            if len(parts) != 5:
                return False
        if self.interval_seconds is not None and self.interval_seconds <= 0:
            return False
        return True


@dataclass
class TaskConfig:
    """任务配置。"""

    task_type: TaskType
    tool_name: str | None = None
    tool_args: dict[str, Any] = field(default_factory=dict)
    prompt: str | None = None
    system_event: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "task_type": self.task_type.value,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "prompt": self.prompt,
            "system_event": self.system_event,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskConfig:
        """从字典创建。"""
        return cls(
            task_type=TaskType(data.get("task_type", "tool_call")),
            tool_name=data.get("tool_name"),
            tool_args=data.get("tool_args", {}),
            prompt=data.get("prompt"),
            system_event=data.get("system_event"),
            extra=data.get("extra", {}),
        )


@dataclass
class ScheduledTaskInfo:
    """定时任务信息（对外暴露的数据结构）。"""

    id: str
    name: str
    description: str | None
    cron_expr: str | None
    interval_seconds: int | None
    one_shot: bool
    task_type: TaskType
    task_config: TaskConfig
    status: TaskStatus
    enabled: bool
    max_retries: int
    retry_count: int
    created_at: datetime
    updated_at: datetime
    last_run_at: datetime | None
    next_run_at: datetime | None
    completed_at: datetime | None
    total_runs: int
    success_runs: int
    failed_runs: int

    @classmethod
    def from_orm(cls, task: Any) -> ScheduledTaskInfo:
        """从 ORM 模型创建。"""
        return cls(
            id=task.id,
            name=task.name,
            description=task.description,
            cron_expr=task.cron_expr,
            interval_seconds=task.interval_seconds,
            one_shot=task.one_shot,
            task_type=TaskType(task.task_type),
            task_config=TaskConfig.from_dict(task.get_task_config()),
            status=TaskStatus(task.status),
            enabled=task.enabled,
            max_retries=task.max_retries,
            retry_count=task.retry_count,
            created_at=task.created_at,
            updated_at=task.updated_at,
            last_run_at=task.last_run_at,
            next_run_at=task.next_run_at,
            completed_at=task.completed_at,
            total_runs=task.total_runs,
            success_runs=task.success_runs,
            failed_runs=task.failed_runs,
        )


@dataclass
class TaskExecutionResult:
    """任务执行结果。"""

    run_id: str
    task_id: str
    status: ExecutionStatus
    started_at: datetime
    finished_at: datetime | None
    duration_ms: float | None
    result_summary: str | None
    error_type: str | None
    error_message: str | None
