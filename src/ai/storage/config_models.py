"""配置类 ORM 模型定义。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel

from src.ai.storage.utils import dt_now as _dt_now


class ProviderConfig(SQLModel, table=True):
    """模型供应商配置。"""

    __tablename__ = "providers"

    id: int | None = Field(default=None, primary_key=True)
    provider_key: str = Field(unique=True, description="供应商唯一键")
    display_name: str | None = Field(default=None, description="显示名称")
    provider_type: str = Field(description="供应商类型，如 openai / azure_openai")
    api_base: str | None = Field(default=None, description="API 基础地址")
    api_key_ciphertext: str | None = Field(
        default=None, description="加密后的 API Key"
    )
    enabled: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=_dt_now, description="创建时间")
    updated_at: datetime = Field(default_factory=_dt_now, description="更新时间")
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )


class ModelConfig(SQLModel, table=True):
    """模型配置。"""

    __tablename__ = "models"

    id: int | None = Field(default=None, primary_key=True)
    model_key: str = Field(unique=True, description="模型唯一键")
    provider_id: int = Field(foreign_key="providers.id", description="所属供应商 ID")
    model_type: str = Field(description="模型类型：chat / embedding / image / tts")
    display_name: str | None = Field(default=None, description="显示名称")
    model_name: str = Field(description="底层模型名")
    context_window: int | None = Field(default=None, description="上下文窗口大小")
    capability_summary: str | None = Field(default=None, description="能力摘要")
    is_default: bool = Field(default=False, description="是否默认模型")
    enabled: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=_dt_now, description="创建时间")
    updated_at: datetime = Field(default_factory=_dt_now, description="更新时间")
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )


class AppSetting(SQLModel, table=True):
    """应用级设置。"""

    __tablename__ = "app_settings"

    id: int | None = Field(default=None, primary_key=True)
    setting_key: str = Field(unique=True, description="设置键")
    display_name: str | None = Field(default=None, description="显示名称")
    setting_value: str = Field(default="", description="设置值")
    value_type: str = Field(default="string", description="值类型")
    encrypted: bool = Field(default=False, description="是否加密存储")
    enabled: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=_dt_now, description="创建时间")
    updated_at: datetime = Field(default_factory=_dt_now, description="更新时间")
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )


class MCPServerRecord(SQLModel, table=True):
    """MCP 服务端配置。"""

    __tablename__ = "mcp_servers"

    id: int | None = Field(default=None, primary_key=True)
    server_key: str = Field(unique=True, description="服务唯一键")
    display_name: str | None = Field(default=None, description="显示名称")
    transport: str = Field(description="传输类型")
    command: str | None = Field(default=None, description="stdio 命令")
    args_json: str = Field(
        default="[]",
        sa_column=Column("args_json", String, nullable=False, server_default="[]"),
        description="命令参数 JSON",
    )
    url: str | None = Field(default=None, description="远程 URL")
    env_json: str = Field(
        default="{}",
        sa_column=Column("env_json", String, nullable=False, server_default="{}"),
        description="环境变量 JSON",
    )
    permission_policy_json: str = Field(
        default="{}",
        sa_column=Column(
            "permission_policy_json", String, nullable=False, server_default="{}"
        ),
        description="权限策略 JSON",
    )
    enabled: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=_dt_now, description="创建时间")
    updated_at: datetime = Field(default_factory=_dt_now, description="更新时间")
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )


class SkillConfig(SQLModel, table=True):
    """技能配置。"""

    __tablename__ = "skills"

    id: int | None = Field(default=None, primary_key=True)
    skill_key: str = Field(unique=True, description="技能唯一键")
    display_name: str | None = Field(default=None, description="显示名称")
    description: str | None = Field(default=None, description="技能描述")
    source_path: str | None = Field(default=None, description="SKILL.md 路径")
    user_invocable: bool = Field(default=True, description="是否允许用户调用")
    disable_model_invocation: bool = Field(
        default=False, description="是否禁止模型自动激活"
    )
    allowed_tools_json: str = Field(
        default="[]",
        sa_column=Column(
            "allowed_tools_json", String, nullable=False, server_default="[]"
        ),
        description="允许的工具列表 JSON",
    )
    enabled: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=_dt_now, description="创建时间")
    updated_at: datetime = Field(default_factory=_dt_now, description="更新时间")
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )


class SecurityPolicy(SQLModel, table=True):
    """安全策略配置。"""

    __tablename__ = "security_policies"

    id: int | None = Field(default=None, primary_key=True)
    policy_key: str = Field(unique=True, description="策略唯一键")
    display_name: str | None = Field(default=None, description="显示名称")
    description: str | None = Field(default=None, description="策略描述")
    policy_type: str = Field(description="策略类型")
    policy_value: str = Field(default="{}", description="策略值 JSON")
    enabled: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=_dt_now, description="创建时间")
    updated_at: datetime = Field(default_factory=_dt_now, description="更新时间")
    extra: str = Field(
        default="{}",
        sa_column=Column("metadata", String, nullable=False, server_default="{}"),
        description="JSON 扩展字段",
    )
