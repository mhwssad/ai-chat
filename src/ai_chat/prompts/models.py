from __future__ import annotations

"""Prompts 模块数据模型 — SQLModel 表 + Pydantic 传输模型。

存储策略:
- inline: 模板内容直接存入 content 字段
- file: 内容存为 data/prompts/*.jinja2 文件，file_path 存相对路径

版本历史:
- prompt_versions 表记录每次更新的快照，支持回滚
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, JSON, Index
from sqlmodel import SQLModel, Field


class PromptTable(SQLModel, table=True):
    """提示词持久化表 — 存储所有提示词的元信息和内容/路径。"""

    __tablename__ = "prompts"
    __table_args__ = (
        Index("ix_prompts_tags", "tags"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    source_type: str = Field(default="inline")  # "inline" | "file"
    content: str = Field(default="")             # inline 模板内容
    file_path: str = Field(default="")           # file 类型相对路径
    input_variables: list = Field(default=[], sa_column=Column("input_variables", JSON))
    description: str = Field(default="")
    tags: str = Field(default="")                 # 逗号分隔的标签（v2 迁移添加）
    is_builtin: bool = Field(default=False)       # 内置提示词标记，不可删除
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PromptVersionTable(SQLModel, table=True):
    """提示词版本历史表 — 记录每次更新的快照。"""

    __tablename__ = "prompt_versions"

    id: Optional[int] = Field(default=None, primary_key=True)
    prompt_name: str = Field(index=True)
    content: str = Field(default="")
    file_path: str = Field(default="")
    source_type: str = Field(default="inline")
    input_variables: list = Field(default=[], sa_column=Column("input_variables", JSON))
    description: str = Field(default="")
    tags: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.now)


class PromptRecord(BaseModel):
    """提示词传输对象 — 在管理器和 CLI/API 之间传递。"""

    id: Optional[int] = None
    name: str
    source_type: str = "inline"
    content: str = ""
    file_path: str = ""
    input_variables: list[str] = []
    description: str = ""
    tags: str = ""
    is_builtin: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PromptVersionRecord(BaseModel):
    """版本历史传输对象。"""

    id: Optional[int] = None
    prompt_name: str
    content: str = ""
    file_path: str = ""
    source_type: str = "inline"
    input_variables: list[str] = []
    description: str = ""
    tags: str = ""
    created_at: Optional[datetime] = None


class PromptCreateRequest(BaseModel):
    """创建提示词的请求模型。"""

    name: str
    content: str = ""
    file_path: str = ""
    source_type: str = "inline"  # "inline" | "file"
    description: str = ""
    tags: str = ""
