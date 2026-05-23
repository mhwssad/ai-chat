"""用量统计路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from src.ai.api.dependencies import db_session
from src.ai.api.schemas.usage import UsageCallsPage, UsageSummary, UsageSummaryByModel
from src.ai.api.services.usage_service import UsageService

router = APIRouter()


@router.get("/summary", response_model=UsageSummary)
async def usage_summary(
    period_days: int = Query(default=30, ge=1, le=365),
    session: Session = Depends(db_session),
):
    return UsageService(session).get_summary(period_days)


@router.get("/by-model", response_model=list[UsageSummaryByModel])
async def usage_by_model(
    period_days: int = Query(default=30, ge=1, le=365),
    session: Session = Depends(db_session),
):
    return UsageService(session).get_summary_by_model(period_days)


@router.get("/calls", response_model=UsageCallsPage)
async def usage_calls(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    model: str | None = Query(default=None),
    status: str | None = Query(default=None),
    session: Session = Depends(db_session),
):
    return UsageService(session).get_calls(limit, offset, model, status)
