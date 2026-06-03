"""提示词路由。"""

from fastapi import APIRouter, Query

from src.ai.api.deps import PromptServiceDep
from src.ai.api.schemas.common import MessageResponse, PaginatedResponse
from src.ai.api.schemas.prompts import (
    PromptCreateRequest,
    PromptRenderRequest,
    PromptRenderResponse,
    PromptResponse,
    PromptRollbackRequest,
    PromptUpdateRequest,
    PromptVersionResponse,
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


def _version_to_response(v) -> PromptVersionResponse:
    """转换 PromptVersionData 为响应格式。"""
    return PromptVersionResponse(
        id=v.id,
        version=v.version,
        template=v.template,
        change_note=v.change_note,
    )


@router.get("", response_model=PaginatedResponse[PromptResponse])
async def list_prompts(
    service: PromptServiceDep,
    category: str | None = None,
    enabled: bool | None = None,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
):
    """列出提示词模板（支持分页）。

    Args:
        category: 按分类过滤。
        enabled: 按启用状态过滤。
        page: 页码（从 1 开始）。
        page_size: 每页数量。
    """
    items, total = service.list_templates_paginated(
        category=category, enabled=enabled, page=page, page_size=page_size
    )
    return PaginatedResponse(
        items=[_prompt_to_response(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


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


@router.patch("/{prompt_key}", response_model=PromptResponse)
async def update_prompt(
    prompt_key: str,
    request: PromptUpdateRequest,
    service: PromptServiceDep,
):
    """部分更新提示词模板（不改模板内容，不产生新版本）。

    Args:
        prompt_key: 提示词键。
        request: 更新请求。
    """
    prompt = service.update_template(
        prompt_key,
        display_name=request.display_name,
        description=request.description,
        category=request.category,
        enabled=request.enabled,
    )
    return _prompt_to_response(prompt)


@router.delete("/{prompt_key}", response_model=MessageResponse)
async def delete_prompt(
    prompt_key: str,
    service: PromptServiceDep,
    permanent: bool = Query(default=False, description="是否永久删除"),
):
    """删除提示词模板。默认软删除（禁用）。

    Args:
        prompt_key: 提示词键。
        permanent: 是否永久删除。
    """
    service.delete_template(prompt_key, permanent=permanent)
    action = "永久删除" if permanent else "已禁用"
    return MessageResponse(message=f"提示词 {prompt_key} {action}")


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


@router.get(
    "/{prompt_key}/versions",
    response_model=list[PromptVersionResponse],
)
async def list_prompt_versions(
    prompt_key: str,
    service: PromptServiceDep,
):
    """列出提示词版本历史。

    Args:
        prompt_key: 提示词键。
    """
    versions = service.list_versions(prompt_key)
    return [_version_to_response(v) for v in versions]


@router.get(
    "/{prompt_key}/versions/{version}",
    response_model=PromptVersionResponse,
)
async def get_prompt_version(
    prompt_key: str,
    version: int,
    service: PromptServiceDep,
):
    """获取提示词指定版本。

    Args:
        prompt_key: 提示词键。
        version: 版本号。
    """
    v = service.get_version(prompt_key, version)
    return _version_to_response(v)


@router.post("/{prompt_key}/rollback", response_model=PromptResponse)
async def rollback_prompt(
    prompt_key: str,
    request: PromptRollbackRequest,
    service: PromptServiceDep,
):
    """回滚提示词到指定版本。

    Args:
        prompt_key: 提示词键。
        request: 回滚请求。
    """
    prompt = service.rollback_template(
        prompt_key, request.version, change_note=request.change_note
    )
    return _prompt_to_response(prompt)
