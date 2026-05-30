"""定时任务 ORM 模型定义。"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel

from src.ai.storage.utils import dt_now as _dt_now


class ScheduledTask(SQLModel, table=True):
    """定时任务表。"""

    __tablename__ = "scheduled_tasks"

    id: str = Field(primary_key=True, description="任务唯一标识（UUID）")
    name: str = Field(description="任务名称")
    description: str | None = Field(default=None, description="任务描述")

    # 调度配置
    cron_expr: str | None = Field(
        default=None, description="Cron 表达式（5 位：分 时 日 月 周）"
    )
    interval_seconds: int | None = Field(
        default=None, description="间隔秒数（与 cron_expr 二选一）"
    )
    one_shot: bool = Field(default=False, description="是否为一次性任务")

    # 任务内容
    task_type: str = Field(
        description="任务类型：tool_call / llm_prompt / system_event"
    )
    task_config: str = Field(
        default="{}",
        sa_column=Column("task_config", String, nullable=False, server_default="{}"),
        description="任务配置 JSON（tool_name + args / prompt 等）",
    )

    # 状态管理
    status: str = Field(
        default="active",
        description="任务状态：active / paused / completed / failed / disabled",
    )
    enabled: bool = Field(default=True, description="是否启用")
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_count: int = Field(default=0, description="当前重试次数")

    # 时间追踪
    created_at: datetime = Field(default_factory=_dt_now, description="创建时间")
    updated_at: datetime = Field(default_factory=_dt_now, description="更新时间")
    last_run_at: datetime | None = Field(default=None, description="上次执行时间")
    next_run_at: datetime | None = Field(default=None, description="下次执行时间")
    completed_at: datetime | None = Field(default=None, description="完成时间")

    # 执行统计
    total_runs: int = Field(default=0, description="总执行次数")
    success_runs: int = Field(default=0, description="成功次数")
    failed_runs: int = Field(default=0, description="失败次数")

    # 扩展字段
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )

    def get_task_config(self) -> dict[str, Any]:
        """安全地获取任务配置字典。"""
        import json

        if not self.task_config:
            return {}
        try:
            return json.loads(self.task_config)
        except json.JSONDecodeError:
            return {}

    def set_task_config(self, data: dict[str, Any]) -> None:
        """将字典安全地序列化为 JSON 字符串。"""
        import json

        self.task_config = json.dumps(data, ensure_ascii=False)

    def get_metadata(self) -> dict[str, Any]:
        """安全地获取元数据字典。"""
        import json

        if not self.extra:
            return {}
        try:
            return json.loads(self.extra)
        except json.JSONDecodeError:
            return {}

    def set_metadata(self, data: dict[str, Any]) -> None:
        """将字典安全地序列化为 JSON 字符串。"""
        import json

        self.extra = json.dumps(data, ensure_ascii=False)


class TaskExecutionLog(SQLModel, table=True):
    """任务执行日志表。"""

    __tablename__ = "task_execution_logs"

    id: int | None = Field(default=None, primary_key=True)
    task_id: str = Field(description="关联任务 ID")
    run_id: str = Field(description="执行唯一标识（UUID）")
    session_id: str | None = Field(default=None, description="关联会话 ID")

    # 执行信息
    status: str = Field(
        default="running",
        description="执行状态：running / success / failed / timeout / cancelled",
    )
    started_at: datetime = Field(default_factory=_dt_now, description="开始时间")
    finished_at: datetime | None = Field(default=None, description="结束时间")
    duration_ms: float | None = Field(default=None, description="执行耗时（毫秒）")

    # 结果
    result_summary: str | None = Field(default=None, description="执行结果摘要")
    error_type: str | None = Field(default=None, description="错误类型")
    error_message: str | None = Field(default=None, description="错误详情")

    # 扩展
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )
