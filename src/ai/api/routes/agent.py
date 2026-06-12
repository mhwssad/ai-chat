"""Agent 路由 — Agent 执行、取消、恢复、团队模式。"""


from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.ai.api.schemas.agent import (
    AgentResultResponse,
    AgentResumeRequest,
    AgentRunRequest,
    AgentTeamRequest,
    AgentTeamResultResponse,
)
from src.ai.api.schemas.common import MessageResponse
from src.ai.core.container import AppContainer
from src.ai.service.agent_service import AgentApiService

router = APIRouter()


@router.post("/run", response_model=AgentResultResponse, summary="运行 Agent")
@inject
async def run_agent(
    req: AgentRunRequest,
    svc: Annotated[
        AgentApiService, Depends(Provide[AppContainer.service_container.agent_service])
    ],
) -> AgentResultResponse:
    """运行 Agent 编排循环（含工具调用）。"""
    result = await svc.run(
        req.session_id,
        req.user_message,
        system_prompt=req.system_prompt,
        max_iterations=req.max_iterations,
        tools=req.tools,
        agent_timeout=req.agent_timeout,
    )
    return AgentResultResponse(**result)


@router.post("/cancel", response_model=MessageResponse, summary="取消运行")
@inject
async def cancel_agent(
    svc: Annotated[
        AgentApiService, Depends(Provide[AppContainer.service_container.agent_service])
    ],
) -> MessageResponse:
    """取消正在执行的 Agent 任务。"""
    cancelled = svc.cancel()
    if cancelled:
        return MessageResponse(message="Agent 任务已取消")
    return MessageResponse(message="没有正在运行的 Agent 任务")


@router.post("/resume", response_model=AgentResultResponse, summary="恢复执行")
@inject
async def resume_agent(
    req: AgentResumeRequest,
    svc: Annotated[
        AgentApiService, Depends(Provide[AppContainer.service_container.agent_service])
    ],
) -> AgentResultResponse:
    """从 checkpoint 恢复 Agent 执行。"""
    result = await svc.resume(
        req.session_id,
        req.user_message,
        max_iterations=req.max_iterations,
        tools=req.tools,
        agent_timeout=req.agent_timeout,
    )
    return AgentResultResponse(**result)


@router.post(
    "/team/orchestrator", response_model=AgentTeamResultResponse, summary="编排者团队"
)
@inject
async def team_orchestrator(
    req: AgentTeamRequest,
    svc: Annotated[
        AgentApiService, Depends(Provide[AppContainer.service_container.agent_service])
    ],
) -> AgentTeamResultResponse:
    """运行编排者团队模式。"""
    result = await svc.run_team_orchestrator(
        req.user_message,
        session_id=req.session_id,
        max_handoffs=req.max_handoffs,
    )
    return AgentTeamResultResponse(**result)


@router.post("/team/debate", response_model=AgentTeamResultResponse, summary="辩论团队")
@inject
async def team_debate(
    req: AgentTeamRequest,
    svc: Annotated[
        AgentApiService, Depends(Provide[AppContainer.service_container.agent_service])
    ],
) -> AgentTeamResultResponse:
    """运行辩论团队模式。"""
    result = await svc.run_team_debate(
        req.user_message,
        session_id=req.session_id,
    )
    return AgentTeamResultResponse(**result)
