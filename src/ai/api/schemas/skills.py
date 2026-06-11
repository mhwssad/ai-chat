"""技能相关响应 Schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SkillIndexResponse(BaseModel):
    """技能索引信息。"""

    name: str = Field(description="技能名称")
    description: str = Field(description="技能描述")
    source_path: str = Field(description="源文件路径")
    user_invocable: bool = Field(default=True, description="用户是否可调用")
    disable_model_invocation: bool = Field(
        default=False, description="是否禁用模型调用"
    )
    argument_hint: str | None = Field(default=None, description="参数提示")


class SlashCommandResponse(BaseModel):
    """斜杠命令信息。"""

    name: str = Field(description="命令名称")
    description: str = Field(description="命令描述")
