"""定时任务 Schema。"""

from typing import Any

from pydantic import BaseModel, Field


class CronTaskCreateRequest(BaseModel):
    """Cron 任务创建请求。"""

    name: str = Field(description="任务名称")
    cron_expr: str = Field(description="Cron 表达式（5 位：分 时 日 月 周）")
    task_type: str = Field(default="tool_call", description="任务类型")
    tool_name: str | None = Field(default=None, description="工具名称")
    tool_args: dict[str, Any] = Field(default_factory=dict, description="工具参数")
    prompt: str | None = Field(default=None, description="LLM 提示")
    description: str | None = Field(default=None, description="任务描述")
    max_retries: int | None = Field(default=None, description="最大重试次数")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class IntervalTaskCreateRequest(BaseModel):
    """间隔任务创建请求。"""

    name: str = Field(description="任务名称")
    interval_seconds: int = Field(description="执行间隔（秒）")
    task_type: str = Field(default="tool_call", description="任务类型")
    tool_name: str | None = Field(default=None, description="工具名称")
    tool_args: dict[str, Any] = Field(default_factory=dict, description="工具参数")
    prompt: str | None = Field(default=None, description="LLM 提示")
    description: str | None = Field(default=None, description="任务描述")
    max_retries: int | None = Field(default=None, description="最大重试次数")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class OneShotTaskCreateRequest(BaseModel):
    """一次性任务创建请求。"""

    name: str = Field(description="任务名称")
    task_type: str = Field(default="tool_call", description="任务类型")
    tool_name: str | None = Field(default=None, description="工具名称")
    tool_args: dict[str, Any] = Field(default_factory=dict, description="工具参数")
    prompt: str | None = Field(default=None, description="LLM 提示")
    description: str | None = Field(default=None, description="任务描述")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class ScheduledTaskResponse(BaseModel):
    """定时任务响应。"""

    id: str = Field(description="任务 ID")
    name: str = Field(description="任务名称")
    description: str | None = Field(default=None, description="任务描述")
    cron_expr: str | None = Field(default=None, description="Cron 表达式")
    interval_seconds: int | None = Field(default=None, description="执行间隔（秒）")
    one_shot: bool = Field(description="是否一次性任务")
    task_type: str = Field(description="任务类型")
    task_config: dict[str, Any] = Field(description="任务配置")
    status: str = Field(description="任务状态")
    enabled: bool = Field(description="是否启用")
    max_retries: int = Field(description="最大重试次数")
    retry_count: int = Field(description="当前重试次数")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")
    last_run_at: str | None = Field(default=None, description="最后执行时间")
    next_run_at: str | None = Field(default=None, description="下次执行时间")
    completed_at: str | None = Field(default=None, description="完成时间")
    total_runs: int = Field(description="总执行次数")
    success_runs: int = Field(description="成功次数")
    failed_runs: int = Field(description="失败次数")


class TaskLogResponse(BaseModel):
    """任务执行日志响应。"""

    run_id: str = Field(description="执行 ID")
    status: str = Field(description="执行状态")
    started_at: str | None = Field(default=None, description="开始时间")
    finished_at: str | None = Field(default=None, description="结束时间")
    duration_ms: float | None = Field(default=None, description="执行时长（毫秒）")
    result_summary: str | None = Field(default=None, description="结果摘要")
    error_type: str | None = Field(default=None, description="错误类型")
    error_message: str | None = Field(default=None, description="错误消息")


class SchedulerStatsResponse(BaseModel):
    """调度器统计响应。"""

    scheduler_running: bool = Field(description="调度器是否运行中")
    scheduler_enabled: bool = Field(description="调度器是否启用")
    total_tasks: int = Field(description="总任务数")
    active_tasks: int = Field(description="活跃任务数")
    completed_tasks: int = Field(description="已完成任务数")
    failed_tasks: int = Field(description="失败任务数")
