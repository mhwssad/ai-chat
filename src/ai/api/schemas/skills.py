"""技能 Schema。"""

from pydantic import BaseModel, Field


class SkillMetadataResponse(BaseModel):
    """技能元数据响应。"""

    name: str = Field(description="技能名称")
    description: str = Field(description="技能描述")
    argument_hint: str | None = Field(default=None, description="参数提示")
    disable_model_invocation: bool = Field(
        default=False, description="是否禁止模型自动激活"
    )
    user_invocable: bool = Field(default=True, description="是否可由用户调用")


class SkillDetailResponse(BaseModel):
    """技能详情响应。"""

    name: str = Field(description="技能名称")
    description: str = Field(description="技能描述")
    source_path: str = Field(description="SKILL.md 文件路径")
    instruction_template: str = Field(description="指令模板")
    disable_model_invocation: bool = Field(
        default=False, description="是否禁止模型自动激活"
    )
    user_invocable: bool = Field(default=True, description="是否可由用户调用")
    allowed_tools: list[str] = Field(default_factory=list, description="允许的工具列表")
    argument_hint: str | None = Field(default=None, description="参数提示")
    model: str | None = Field(default=None, description="指定模型")
    context_fork: bool = Field(default=False, description="是否使用上下文分叉")
    agent_type: str | None = Field(default=None, description="Agent 类型")


class SkillActivateRequest(BaseModel):
    """技能激活请求。"""

    arguments: str = Field(default="", description="用户输入参数")


class SkillActivateResponse(BaseModel):
    """技能激活响应。"""

    name: str = Field(description="技能名称")
    content: str = Field(description="渲染后的指令内容")
