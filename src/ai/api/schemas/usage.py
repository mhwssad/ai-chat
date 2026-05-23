"""用量统计 API schema。"""

from __future__ import annotations

from pydantic import BaseModel


class UsageSummary(BaseModel):
    """聚合用量统计。"""

    total_calls: int
    success_calls: int
    error_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost: float
    currency: str
    avg_duration_ms: float | None
    error_rate: float


class UsageSummaryByModel(BaseModel):
    """按模型分组的用量统计。"""

    model: str
    provider: str
    calls: int
    total_tokens: int
    total_cost: float


class UsageCallItem(BaseModel):
    """单条调用记录。"""

    id: int
    session_id: str | None
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    total_cost: float | None
    currency: str | None
    duration_ms: float | None
    status: str
    error_type: str | None
    created_at: str


class UsageCallsPage(BaseModel):
    """调用记录分页。"""

    items: list[UsageCallItem]
    total: int
    limit: int
    offset: int
