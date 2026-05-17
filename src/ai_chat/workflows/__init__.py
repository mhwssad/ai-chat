"""Workflows 模块 — 可组合工作流引擎。"""

from .models import (
    EdgeConfig,
    NodeConfig,
    WorkflowConfig,
    WorkflowCreateRequest,
    WorkflowRecord,
    WorkflowTable,
)
from .state import WorkflowState, extract_last_human_message
from .nodes import NodeExecutorFactory
from .engine import WorkflowEngine, WorkflowEngineError, validate_workflow
from .store import WorkflowStore
from .manager import WorkflowManager, workflow_manager
from .menu import menu_workflows

__all__ = [
    # 模型
    "NodeConfig",
    "EdgeConfig",
    "WorkflowConfig",
    "WorkflowTable",
    "WorkflowRecord",
    "WorkflowCreateRequest",
    # 状态
    "WorkflowState",
    "extract_last_human_message",
    # 节点
    "NodeExecutorFactory",
    # 引擎
    "WorkflowEngine",
    "WorkflowEngineError",
    "validate_workflow",
    # 持久化
    "WorkflowStore",
    # 管理
    "WorkflowManager",
    "workflow_manager",
    # 菜单
    "menu_workflows",
]
