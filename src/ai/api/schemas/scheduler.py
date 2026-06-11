"""定时任务相关请求/响应 Schema。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SchedulerCreateCronRequest(BaseModel):
    """创建 cron 定时任务请求。"""

    name: str = Field(..., min_length=1, description="任务名称")
    cron_expr: str = Field(..., min_length=9, description="Cron 表达式（5 位）")
    task_type: str = Field(
        default="tool_call", description="任务类型（tool_call/llm_prompt/system_event）"
    )
    tool_name: str | None = Field(default=None, description="工具名称")
    tool_args: dict[str, Any] = Field(default_factory=dict, description="工具参数")
    prompt: str | None = Field(default=None, description="LLM 提示词")
    description: str | None = Field(default=None, description="任务描述")
    max_retries: int = Field(default=3, ge=0, description="最大重试次数")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class SchedulerCreateIntervalRequest(BaseModel):
    """创建间隔任务请求。"""

    name: str = Field(..., min_length=1, description="任务名称")
    interval_seconds: int = Field(..., gt=0, description="间隔秒数")
    task_type: str = Field(default="tool_call", description="任务类型")
    tool_name: str | None = Field(default=None, description="工具名称")
    tool_args: dict[str, Any] = Field(default_factory=dict, description="工具参数")
    prompt: str | None = Field(default=None, description="LLM 提示词")
    description: str | None = Field(default=None, description="任务描述")
    max_retries: int = Field(default=3, ge=0, description="最大重试次数")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class SchedulerCreateOneShotRequest(BaseModel):
    """创建一次性任务请求。"""

    name: str = Field(..., min_length=1, description="任务名称")
    task_type: str = Field(default="tool_call", description="任务类型")
    tool_name: str | None = Field(default=None, description="工具名称")
    tool_args: dict[str, Any] = Field(default_factory=dict, description="工具参数")
    prompt: str | None = Field(default=None, description="LLM 提示词")
    description: str | None = Field(default=None, description="任务描述")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class ScheduledTaskResponse(BaseModel):
    """定时任务信息。"""

    id: str = Field(description="任务 ID")
    name: str = Field(description="任务名称")
    description: str | None = Field(default=None, description="描述")
    cron_expr: str | None = Field(default=None, description="Cron 表达式")
    interval_seconds: int | None = Field(default=None, description="间隔秒数")
    one_shot: bool = Field(default=False, description="是否一次性任务")
    task_type: str = Field(description="任务类型")
    task_config: dict[str, Any] = Field(default_factory=dict, description="任务配置")
    status: str = Field(description="任务状态")
    enabled: bool = Field(default=True, description="是否启用")
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_count: int = Field(default=0, description="当前重试次数")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")
    last_run_at: str | None = Field(default=None, description="上次执行时间")
    next_run_at: str | None = Field(default=None, description="下次执行时间")
    completed_at: str | None = Field(default=None, description="完成时间")
    total_runs: int = Field(default=0, description="总执行次数")
    success_runs: int = Field(default=0, description="成功次数")
    failed_runs: int = Field(default=0, description="失败次数")


class TaskLogResponse(BaseModel):
    """任务执行日志。"""

    run_id: str = Field(description="执行 ID")
    task_id: str = Field(description="任务 ID")
    status: str = Field(description="执行状态")
    started_at: str | None = Field(default=None, description="开始时间")
    finished_at: str | None = Field(default=None, description="结束时间")
    duration_ms: float | None = Field(default=None, description="耗时毫秒")
    result_summary: str | None = Field(default=None, description="结果摘要")
    error_type: str | None = Field(default=None, description="错误类型")
    error_message: str | None = Field(default=None, description="错误信息")


class SchedulerStatsResponse(BaseModel):
    """调度器统计信息。"""

    scheduler_running: bool = Field(description="调度器是否运行中")
    total_tasks: int = Field(default=0, description="总任务数")
    active_tasks: int = Field(default=0, description="活跃任务数")
    paused_tasks: int = Field(default=0, description="暂停任务数")
    disabled_tasks: int = Field(default=0, description="禁用任务数")
