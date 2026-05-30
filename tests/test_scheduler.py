"""定时任务模块测试。"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from src.ai.core.scheduler.types import (
    CronSpec,
    ExecutionStatus,
    ScheduledTaskInfo,
    TaskConfig,
    TaskStatus,
    TaskType,
)


def test_cron_spec_validation():
    """测试 Cron 规范验证。"""
    # 有效的 Cron 表达式
    spec1 = CronSpec(cron_expr="0 9 * * *")
    assert spec1.validate() is True

    # 有效的间隔配置
    spec2 = CronSpec(interval_seconds=3600)
    assert spec2.validate() is True

    # 有效的一次性任务
    spec3 = CronSpec(one_shot=True)
    assert spec3.validate() is True

    # 无效：同时指定 cron 和 interval
    spec4 = CronSpec(cron_expr="0 9 * * *", interval_seconds=3600)
    assert spec4.validate() is False

    # 无效：无任何配置
    spec5 = CronSpec()
    assert spec5.validate() is False

    # 无效：Cron 表达式格式错误
    spec6 = CronSpec(cron_expr="0 9 * *")
    assert spec6.validate() is False

    # 无效：间隔为 0
    spec7 = CronSpec(interval_seconds=0)
    assert spec7.validate() is False


def test_task_config_serialization():
    """测试任务配置序列化。"""
    config = TaskConfig(
        task_type=TaskType.TOOL_CALL,
        tool_name="CronList",
        tool_args={"limit": 10},
    )

    # 序列化为字典
    data = config.to_dict()
    assert data["task_type"] == "tool_call"
    assert data["tool_name"] == "CronList"
    assert data["tool_args"] == {"limit": 10}

    # 从字典反序列化
    restored = TaskConfig.from_dict(data)
    assert restored.task_type == TaskType.TOOL_CALL
    assert restored.tool_name == "CronList"
    assert restored.tool_args == {"limit": 10}


def test_task_status_enum():
    """测试任务状态枚举。"""
    assert TaskStatus.ACTIVE.value == "active"
    assert TaskStatus.PAUSED.value == "paused"
    assert TaskStatus.COMPLETED.value == "completed"
    assert TaskStatus.FAILED.value == "failed"
    assert TaskStatus.DISABLED.value == "disabled"


def test_task_type_enum():
    """测试任务类型枚举。"""
    assert TaskType.TOOL_CALL.value == "tool_call"
    assert TaskType.LLM_PROMPT.value == "llm_prompt"
    assert TaskType.SYSTEM_EVENT.value == "system_event"


def test_execution_status_enum():
    """测试执行状态枚举。"""
    assert ExecutionStatus.RUNNING.value == "running"
    assert ExecutionStatus.SUCCESS.value == "success"
    assert ExecutionStatus.FAILED.value == "failed"
    assert ExecutionStatus.TIMEOUT.value == "timeout"
    assert ExecutionStatus.CANCELLED.value == "cancelled"


def test_scheduled_task_info_from_orm():
    """测试从 ORM 模型创建任务信息。"""
    # 模拟 ORM 对象
    mock_task = MagicMock()
    mock_task.id = "test-id-123"
    mock_task.name = "test-task"
    mock_task.description = "测试任务"
    mock_task.cron_expr = "0 9 * * *"
    mock_task.interval_seconds = None
    mock_task.one_shot = False
    mock_task.task_type = "llm_prompt"
    mock_task.get_task_config.return_value = {
        "task_type": "llm_prompt",
        "prompt": "Hello",
    }
    mock_task.status = "active"
    mock_task.enabled = True
    mock_task.max_retries = 3
    mock_task.retry_count = 0
    mock_task.created_at = datetime.now()
    mock_task.updated_at = datetime.now()
    mock_task.last_run_at = None
    mock_task.next_run_at = datetime.now()
    mock_task.completed_at = None
    mock_task.total_runs = 0
    mock_task.success_runs = 0
    mock_task.failed_runs = 0

    # 创建任务信息
    info = ScheduledTaskInfo.from_orm(mock_task)

    assert info.id == "test-id-123"
    assert info.name == "test-task"
    assert info.task_type == TaskType.LLM_PROMPT
    assert info.status == TaskStatus.ACTIVE
    assert info.enabled is True
    assert info.cron_expr == "0 9 * * *"


def test_service_validation():
    """测试服务层验证逻辑。"""
    from src.ai.core.scheduler.service import SchedulerService

    # 创建 mock 对象
    mock_manager = MagicMock()
    mock_store = MagicMock()
    mock_settings = MagicMock()
    mock_settings.scheduler_default_max_retries = 3

    service = SchedulerService(
        manager=mock_manager,
        store=mock_store,
        settings=mock_settings,
    )

    # 测试无效的 Cron 表达式
    with pytest.raises(ValueError, match="Cron 表达式不能为空"):
        service._validate_cron_expr("")

    with pytest.raises(ValueError, match="无效的 Cron 表达式"):
        service._validate_cron_expr("0 9 * *")

    # 测试无效的间隔
    with pytest.raises(ValueError, match="间隔秒数必须大于 0"):
        service._validate_interval(0)

    with pytest.raises(ValueError, match="间隔秒数必须大于 0"):
        service._validate_interval(-1)

    # 测试任务配置验证
    with pytest.raises(ValueError, match="工具调用任务必须指定 tool_name"):
        service._validate_task_config(
            task_type=TaskType.TOOL_CALL,
            tool_name=None,
            tool_args=None,
            prompt=None,
        )

    with pytest.raises(ValueError, match="LLM 提示任务必须指定 prompt"):
        service._validate_task_config(
            task_type=TaskType.LLM_PROMPT,
            tool_name=None,
            tool_args=None,
            prompt=None,
        )


def test_manager_scheduling():
    """测试管理器调度逻辑。"""
    from src.ai.core.scheduler.manager import SchedulerManager

    # 创建 mock 对象
    mock_settings = MagicMock()
    mock_settings.scheduler_enabled = True
    mock_settings.scheduler_check_interval = 30
    mock_settings.scheduler_max_concurrent = 5
    mock_settings.scheduler_task_timeout = 300
    mock_settings.scheduler_cleanup_days = 30

    mock_store = MagicMock()
    mock_store.get_due_tasks.return_value = []
    mock_store.cleanup_old_logs.return_value = 0

    manager = SchedulerManager(
        settings=mock_settings,
        store=mock_store,
    )

    # 测试 calculate_next_run
    mock_task = MagicMock()
    mock_task.one_shot = False
    mock_task.cron_expr = "0 9 * * *"
    mock_task.interval_seconds = None

    next_run = manager.calculate_next_run(mock_task)
    assert next_run is not None
    assert isinstance(next_run, datetime)

    # 测试一次性任务
    mock_task.one_shot = True
    next_run = manager.calculate_next_run(mock_task)
    assert next_run is None

    # 测试间隔任务
    mock_task.one_shot = False
    mock_task.cron_expr = None
    mock_task.interval_seconds = 3600

    next_run = manager.calculate_next_run(mock_task)
    assert next_run is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
