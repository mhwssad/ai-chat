"""数据库管理型配置表。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import Column, Index, String
from sqlmodel import Field, SQLModel

from src.ai.storage.base_repository import BaseRepository


def _dt_now() -> datetime:
    return datetime.now()


class AppSetting(SQLModel, table=True):
    """基础系统设置。"""

    __tablename__ = "app_settings"

    setting_key: str = Field(primary_key=True)
    setting_value: str
    value_type: str = Field(default="string")
    description: str | None = None
    updated_at: datetime = Field(default_factory=_dt_now)
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
    )


class MCPServer(SQLModel, table=True):
    """MCP server 配置。"""

    __tablename__ = "mcp_servers"
    __table_args__ = (
        Index("idx_mcp_servers_enabled", "enabled"),
        Index("idx_mcp_servers_status", "status"),
    )

    id: int | None = Field(default=None, primary_key=True)
    server_key: str = Field(unique=True)
    display_name: str | None = None
    transport: str
    command: str | None = None
    args: str = Field(
        default="[]",
        sa_column=Column(String, nullable=False, server_default="[]"),
    )
    url: str | None = None
    env: str = Field(
        default="{}",
        sa_column=Column(String, nullable=False, server_default="{}"),
    )
    permission_policy: str = Field(
        default="{}",
        sa_column=Column(String, nullable=False, server_default="{}"),
    )
    enabled: bool = Field(default=True)
    status: str = Field(default="unknown")
    last_checked_at: datetime | None = None
    created_at: datetime = Field(default_factory=_dt_now)
    updated_at: datetime = Field(default_factory=_dt_now)
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
    )


class Skill(SQLModel, table=True):
    """Skill 配置和发现结果。"""

    __tablename__ = "skills"
    __table_args__ = (Index("idx_skills_enabled", "enabled"),)

    id: int | None = Field(default=None, primary_key=True)
    skill_key: str = Field(unique=True)
    display_name: str | None = None
    description: str | None = None
    version: str | None = None
    source_path: str | None = None
    capabilities: str = Field(
        default="[]",
        sa_column=Column(String, nullable=False, server_default="[]"),
    )
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_dt_now)
    updated_at: datetime = Field(default_factory=_dt_now)
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
    )

    def get_capabilities(self) -> list[str]:
        try:
            data = json.loads(self.capabilities or "[]")
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    def set_capabilities(self, values: list[str]) -> None:
        self.capabilities = json.dumps(values, ensure_ascii=False)

    def get_metadata(self) -> dict[str, Any]:
        try:
            data = json.loads(self.extra or "{}")
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def set_metadata(self, data: dict[str, Any]) -> None:
        self.extra = json.dumps(data, ensure_ascii=False)


class SecurityPolicy(SQLModel, table=True):
    """安全策略。"""

    __tablename__ = "security_policies"
    __table_args__ = (Index("idx_security_policies_scope_enabled", "scope", "enabled"),)

    id: int | None = Field(default=None, primary_key=True)
    policy_key: str = Field(unique=True)
    scope: str
    rule: str
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_dt_now)
    updated_at: datetime = Field(default_factory=_dt_now)
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
    )


class AppSettingRepository(BaseRepository[AppSetting]):
    model = AppSetting


class MCPServerRepository(BaseRepository[MCPServer]):
    model = MCPServer


class SkillRepository(BaseRepository[Skill]):
    model = Skill

    def get_by_key(self, skill_key: str) -> Skill | None:
        return self.get_by_field("skill_key", skill_key)

    def get_enabled(self) -> list[Skill]:
        return self.list(enabled=True, order_by="skill_key", descending=False)

    def upsert_discovered(
        self,
        *,
        skill_key: str,
        display_name: str | None,
        description: str | None,
        version: str | None,
        source_path: str,
        capabilities: list[str],
        metadata: dict[str, Any],
        enabled: bool = True,
    ) -> Skill:
        skill = self.get_by_key(skill_key)
        if skill is None:
            skill = Skill(
                skill_key=skill_key,
                display_name=display_name,
                description=description,
                version=version,
                source_path=source_path,
                enabled=enabled,
            )
            skill.set_capabilities(capabilities)
            skill.set_metadata(metadata)
            return self.save(skill)
        skill = self.update(
            skill,
            display_name=display_name,
            description=description,
            version=version,
            source_path=source_path,
            enabled=skill.enabled,
        )
        skill.set_capabilities(capabilities)
        skill.set_metadata(metadata)
        return self.save(skill)


class SecurityPolicyRepository(BaseRepository[SecurityPolicy]):
    model = SecurityPolicy
