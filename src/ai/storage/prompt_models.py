"""提示词数据库模型。"""

from datetime import datetime

from sqlalchemy import Column, Index, String
from sqlmodel import Field, SQLModel

from src.ai.storage.utils import dt_now as _dt_now


class PromptTemplate(SQLModel, table=True):
    """提示词模板。"""

    __tablename__ = "prompt_templates"
    __table_args__ = (
        Index("idx_prompt_templates_enabled", "enabled"),
        Index("idx_prompt_templates_category", "category"),
    )

    id: int | None = Field(default=None, primary_key=True)
    prompt_key: str = Field(unique=True)
    display_name: str | None = None
    description: str | None = None
    category: str = Field(default="general")
    template: str
    template_format: str = Field(default="jinja2")
    version: int = Field(default=1)
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_dt_now)
    updated_at: datetime = Field(default_factory=_dt_now)
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
    )


class PromptVersion(SQLModel, table=True):
    """提示词模板历史版本。"""

    __tablename__ = "prompt_versions"
    __table_args__ = (Index("idx_prompt_versions_prompt", "prompt_id", "version"),)

    id: int | None = Field(default=None, primary_key=True)
    prompt_id: int = Field(foreign_key="prompt_templates.id")
    version: int
    template: str
    change_note: str | None = None
    created_at: datetime = Field(default_factory=_dt_now)
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
    )
