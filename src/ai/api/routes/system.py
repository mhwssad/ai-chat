"""系统状态路由。"""


from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.ai.api.schemas.system import ConfigSummaryResponse, SystemStatusResponse
from src.ai.core.container import AppContainer
from src.ai.service.system_service import SystemService

router = APIRouter()


@router.get("/status", response_model=SystemStatusResponse, summary="获取运行状态")
@inject
async def get_system_status(
    svc: Annotated[
        SystemService, Depends(Provide[AppContainer.service_container.system_service])
    ],
) -> SystemStatusResponse:
    """返回系统运行状态摘要。"""
    status = svc.get_runtime_status()
    return SystemStatusResponse(**status)


@router.get("/config", response_model=ConfigSummaryResponse, summary="获取配置摘要")
@inject
async def get_system_config(
    svc: Annotated[
        SystemService, Depends(Provide[AppContainer.service_container.system_service])
    ],
) -> ConfigSummaryResponse:
    """返回关键配置摘要。"""
    config = svc.get_config_summary()
    return ConfigSummaryResponse(**config)
