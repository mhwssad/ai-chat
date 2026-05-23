"""用量统计服务。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlmodel import Session

from src.ai.api.schemas.usage import UsageCallItem, UsageCallsPage
from src.ai.storage.runtime_repository import ModelCallRepository


class UsageService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = ModelCallRepository(session)

    def get_summary(self, period_days: int = 30) -> dict[str, Any]:
        since = datetime.now() - timedelta(days=period_days)
        stats = self._repo.get_aggregated_stats(since=since)
        stats["currency"] = "USD"
        return stats

    def get_summary_by_model(self, period_days: int = 30) -> list[dict[str, Any]]:
        since = datetime.now() - timedelta(days=period_days)
        return self._repo.get_stats_by_model(since=since)

    def get_calls(
        self,
        limit: int = 50,
        offset: int = 0,
        model: str | None = None,
        status: str | None = None,
    ) -> UsageCallsPage:
        filters: dict[str, Any] = {}
        if model:
            filters["model"] = model
        if status:
            filters["status"] = status
        page = self._repo.paginate(limit=limit, offset=offset, order_by="created_at", descending=True, **filters)
        items = [
            UsageCallItem(
                id=c.id,
                session_id=c.session_id,
                provider=c.provider,
                model=c.model,
                input_tokens=c.input_tokens,
                output_tokens=c.output_tokens,
                total_tokens=c.total_tokens,
                total_cost=c.total_cost,
                currency=c.currency,
                duration_ms=c.duration_ms,
                status=c.status,
                error_type=c.error_type,
                created_at=c.created_at.isoformat() if c.created_at else "",
            )
            for c in page.items
        ]
        return UsageCallsPage(items=items, total=page.total, limit=page.limit, offset=page.offset)
