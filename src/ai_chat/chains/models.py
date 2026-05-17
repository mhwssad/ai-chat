"""Chains 数据模型 — SQLModel 持久化表 + Pydantic 传输对象。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlmodel import SQLModel, Field


class ChainTable(SQLModel, table=True):
    """链配置持久化表。"""

    __tablename__ = "chains"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    chain_type: str = ""           # chat/summarize/translate/...
    model_name: str = ""           # 使用的模型名称
    config: str = "{}"             # JSON: ChainConfig 参数
    prompt_context: str = "{}"     # JSON: 模板变量
    description: str = ""
    tags: str = ""                 # 逗号分隔标签
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ChainRecord(BaseModel):
    """链配置传输对象。"""

    id: Optional[int] = None
    name: str
    chain_type: str = ""
    model_name: str = ""
    config: dict = {}
    prompt_context: dict = {}
    description: str = ""
    tags: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ChainCreateRequest(BaseModel):
    """创建链的请求模型。"""

    name: str
    chain_type: str
    model_name: str = ""
    config: dict = {}
    prompt_context: dict = {}
    description: str = ""
    tags: str = ""
