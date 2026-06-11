"""技能管理路由 — 发现、列表、详情、斜杠命令。"""

from __future__ import annotations

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException

from src.ai.api.schemas.skills import SkillIndexResponse, SlashCommandResponse
from src.ai.core.container import AppContainer
from src.ai.service.skill_service import SkillApiService

router = APIRouter()


@router.get("", response_model=list[SkillIndexResponse], summary="列出技能")
@inject
async def list_skills(
    svc: Annotated[
        SkillApiService,
        Depends(Provide[AppContainer.service_container.skill_api_service]),
    ],
) -> list[SkillIndexResponse]:
    """列出所有技能。"""
    skills = svc.list_skills()
    return [SkillIndexResponse(**s) for s in skills]


@router.post(
    "/discover", response_model=list[SkillIndexResponse], summary="重新发现技能"
)
@inject
async def discover_skills(
    svc: Annotated[
        SkillApiService,
        Depends(Provide[AppContainer.service_container.skill_api_service]),
    ],
) -> list[SkillIndexResponse]:
    """重新扫描技能目录。"""
    skills = svc.discover()
    return [SkillIndexResponse(**s) for s in skills]


@router.get(
    "/commands", response_model=list[SlashCommandResponse], summary="斜杠命令列表"
)
@inject
async def get_slash_commands(
    svc: Annotated[
        SkillApiService,
        Depends(Provide[AppContainer.service_container.skill_api_service]),
    ],
) -> list[SlashCommandResponse]:
    """获取可用的斜杠命令列表。"""
    commands = svc.get_slash_commands()
    return [SlashCommandResponse(**c) for c in commands]


@router.get("/{name}", response_model=SkillIndexResponse, summary="获取技能")
@inject
async def get_skill(
    name: str,
    svc: Annotated[
        SkillApiService,
        Depends(Provide[AppContainer.service_container.skill_api_service]),
    ],
) -> SkillIndexResponse:
    """获取指定技能。"""
    skill = svc.get_skill(name)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"技能不存在: {name}")
    return SkillIndexResponse(**skill)
