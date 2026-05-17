"""Workflows 数据模型 — SQLModel 持久化表 + Pydantic 传输对象。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlmodel import SQLModel, Field


# ── JSON 内嵌配置模型 ─────────────────────────────────


class NodeConfig(BaseModel):
    """单个节点的声明式配置。"""

    name: str                       # 节点唯一标识
    type: str                       # chain | llm | agent | classifier | input | output
    ref: str = ""                   # chain 名称 / agent 名称
    prompt_key: str = ""            # llm/classifier 节点的 prompt
    prompt_context: dict = {}       # 模板变量
    model_name: str = ""            # 节点级模型覆盖
    allowed_intents: list[str] = []  # classifier 可选路由键
    config: dict = {}               # 节点级额外配置


class EdgeConfig(BaseModel):
    """一条边的声明式配置。"""

    type: str                       # direct | conditional
    source: str                     # 源节点名
    target: str = ""                # direct 边目标
    conditions: dict[str, str] = {}  # conditional: {intent: target}


class WorkflowConfig(BaseModel):
    """工作流级别运行配置。"""

    default_model: str = ""
    max_retries: int = 2
    timeout: int = 120


# ── SQLModel 持久化表 ─────────────────────────────────


class WorkflowTable(SQLModel, table=True):
    """工作流配置持久化表。"""

    __tablename__ = "workflows"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str = ""
    model_name: str = ""
    nodes: str = "[]"               # JSON: list[NodeConfig]
    edges: str = "[]"               # JSON: list[EdgeConfig]
    config: str = "{}"              # JSON: WorkflowConfig
    tags: str = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ── Pydantic 传输对象 ─────────────────────────────────


class WorkflowRecord(BaseModel):
    """工作流传输对象。"""

    id: Optional[int] = None
    name: str
    description: str = ""
    model_name: str = ""
    nodes: list[NodeConfig] = []
    edges: list[EdgeConfig] = []
    config: WorkflowConfig = WorkflowConfig()
    tags: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WorkflowCreateRequest(BaseModel):
    """创建工作流的请求模型。"""

    name: str
    description: str = ""
    model_name: str = ""
    nodes: list[NodeConfig] = []
    edges: list[EdgeConfig] = []
    config: WorkflowConfig = WorkflowConfig()
    tags: str = ""
