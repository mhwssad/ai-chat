"""提示词路由。"""

from fastapi import APIRouter

from src.ai.api.deps import PromptServiceDep
from src.ai.api.schemas.prompts import (
    PromptCreateRequest,
    PromptRenderRequest,
    PromptRenderResponse,
    PromptResponse,
)
from src.ai.core.prompts.types import PromptRenderRequest as CorePromptRenderRequest

router = APIRouter(prefix="/prompts", tags=["prompts"])


def _prompt_to_response(prompt) -> PromptResponse:
    """转换 PromptData 为响应格式。"""
    return PromptResponse(
        prompt_key=prompt.prompt_key,
        template=prompt.template,
        version=prompt.version,
        display_name=prompt.display_name,
        description=prompt.description,
        category=prompt.category,
        enabled=prompt.enabled,
    )


@router.get("", response_model=list[PromptResponse])
async def list_prompts(
    service: PromptServiceDep,
    category: str | None = None,
):
    """列出提示词模板。

    Args:
        category: 按分类过滤。
    """
    templates = service.list_templates(category=category)
    return [_prompt_to_response(t) for t in templates]


@router.get("/{prompt_key}", response_model=PromptResponse)
async def get_prompt(prompt_key: str, service: PromptServiceDep):
    """获取提示词模板。

    Args:
        prompt_key: 提示词键。
    """
    prompt = service.get_template(prompt_key)
    if prompt is None:
        from src.ai.exception.prompt_exception import PromptNotFoundError

        raise PromptNotFoundError(
            f"提示词不存在: {prompt_key}", context={"prompt_key": prompt_key}
        )

    return _prompt_to_response(prompt)


@router.post("", response_model=PromptResponse)
async def create_or_update_prompt(
    request: PromptCreateRequest,
    service: PromptServiceDep,
):
    """创建或更新提示词模板。

    Args:
        request: 创建/更新请求。
    """
    prompt = service.save_template(
        prompt_key=request.prompt_key,
        template=request.template,
        display_name=request.display_name,
        description=request.description,
        category=request.category,
        change_note=request.change_note,
    )
    return _prompt_to_response(prompt)


@router.post("/render", response_model=PromptRenderResponse)
async def render_prompt(
    request: PromptRenderRequest,
    service: PromptServiceDep,
):
    """渲染提示词模板。

    Args:
        request: 渲染请求。
    """
    core_request = CorePromptRenderRequest(
        prompt_key=request.prompt_key,
        variables=request.variables,
    )
    result = service.render(core_request)

    return PromptRenderResponse(
        prompt_key=result.prompt_key,
        content=result.content,
        version=result.version,
        metadata=result.metadata,
    )
