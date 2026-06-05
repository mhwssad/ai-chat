"""技能路由。"""

from fastapi import APIRouter

from src.ai.api.deps import SkillServiceDep
from src.ai.api.schemas.skills import (
    SkillActivateRequest,
    SkillActivateResponse,
    SkillDetailResponse,
    SkillEnabledRequest,
    SkillMetadataResponse,
)

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillMetadataResponse])
async def list_skills(service: SkillServiceDep):
    """列出所有技能。"""
    metadata = service.get_skill_metadata()
    return [
        SkillMetadataResponse(
            name=m.name,
            description=m.description,
            enabled=m.enabled,
            argument_hint=m.argument_hint,
            disable_model_invocation=m.disable_model_invocation,
            user_invocable=m.user_invocable,
        )
        for m in metadata
    ]


@router.get("/{name}", response_model=SkillDetailResponse)
async def get_skill(name: str, service: SkillServiceDep):
    """获取技能详情。

    Args:
        name: 技能名称。
    """
    defn = service.get(name)
    if defn is None:
        from src.ai.exception.skill_exception import SkillNotFoundError

        raise SkillNotFoundError(f"技能不存在: {name}", context={"name": name})

    return SkillDetailResponse(
        name=defn.name,
        description=defn.description,
        enabled=defn.enabled,
        source_path=str(defn.source_path),
        instruction_template=defn.instruction_template,
        disable_model_invocation=defn.disable_model_invocation,
        user_invocable=defn.user_invocable,
        allowed_tools=defn.allowed_tools,
        argument_hint=defn.argument_hint,
        model=defn.model,
        context_fork=defn.context_fork,
        agent_type=defn.agent_type,
    )


@router.post("/{name}/activate", response_model=SkillActivateResponse)
async def activate_skill(
    name: str,
    request: SkillActivateRequest,
    service: SkillServiceDep,
):
    """激活技能，渲染完整指令内容。

    Args:
        name: 技能名称。
        request: 激活请求。
    """
    content = service.activate(name, arguments=request.arguments)
    return SkillActivateResponse(name=name, content=content)


@router.post("/{name}/enabled", response_model=SkillDetailResponse)
async def set_skill_enabled(
    name: str,
    request: SkillEnabledRequest,
    service: SkillServiceDep,
):
    """设置技能启用状态。"""
    defn = service.set_enabled(name, request.enabled)
    return SkillDetailResponse(
        name=defn.name,
        description=defn.description,
        enabled=defn.enabled,
        source_path=str(defn.source_path),
        instruction_template=defn.instruction_template,
        disable_model_invocation=defn.disable_model_invocation,
        user_invocable=defn.user_invocable,
        allowed_tools=defn.allowed_tools,
        argument_hint=defn.argument_hint,
        model=defn.model,
        context_fork=defn.context_fork,
        agent_type=defn.agent_type,
    )
