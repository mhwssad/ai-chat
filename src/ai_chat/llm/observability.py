"""可观测性模块 — LLM 调用量统计、延迟监控与错误追踪。

提供三个核心能力：
- UsageTracker：将每次调用的 token 消耗、延迟等写入 SQLite
- ErrorLogger：将失败的请求追加写入 JSONL 文件
- LLMUsageLog：SQLModel 表定义

用法::

    from src.ai_chat.llm.observability import usage_tracker, error_logger

    usage_tracker.record(UsageEntry(provider="openai", model="gpt-4o", ...))
    error_logger.log_error("openai", "gpt-4o", exception, duration_ms=1200)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlmodel import Field as SQLField
from sqlmodel import Session as SqlSession
from sqlmodel import SQLModel, create_engine, select

from src.ai_chat.config.base_config import project_root
from src.ai_chat.config.logging_setup import get_logger

logger = get_logger(__name__)


# ======================================================================
# 数据模型
# ======================================================================


@dataclass
class UsageEntry:
    """单次调用使用量记录（传输对象）。"""

    provider: str
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    duration_ms: float = 0.0
    success: bool = True
    error_type: Optional[str] = None


class LLMUsageLog(SQLModel, table=True):
    """LLM 调用使用量日志表。"""

    __tablename__ = "llm_usage_logs"

    id: Optional[int] = SQLField(default=None, primary_key=True)
    provider: str
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    duration_ms: float = 0.0
    success: bool = True
    error_type: Optional[str] = None
    timestamp: datetime = SQLField(default_factory=datetime.now)


# ======================================================================
# 使用量追踪器
# ======================================================================


class UsageTracker:
    """LLM 使用量追踪器 — 记录每次调用的 token 消耗和耗时到 SQLite。

    使用独立的 observability.db，与 memory.db 分离，
    避免高频日志写入影响会话存储性能。
    """

    def __init__(self, db_path: str = "") -> None:
        db_path = db_path or str(project_root / "data" / "observability.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        SQLModel.metadata.create_all(self._engine)
        logger.info("UsageTracker 初始化完成: db=%s", db_path)

    def record(self, entry: UsageEntry) -> None:
        """记录一次调用的使用量。"""
        row = LLMUsageLog(
            provider=entry.provider,
            model=entry.model,
            input_tokens=entry.input_tokens,
            output_tokens=entry.output_tokens,
            total_tokens=entry.total_tokens,
            duration_ms=round(entry.duration_ms, 1),
            success=entry.success,
            error_type=entry.error_type,
        )
        with SqlSession(self._engine) as session:
            session.add(row)
            session.commit()
        logger.debug(
            "记录使用量: provider=%s, model=%s, tokens=%s, duration=%.0fms, success=%s",
            entry.provider,
            entry.model,
            entry.total_tokens,
            entry.duration_ms,
            entry.success,
        )

    def get_recent(
        self, limit: int = 100, provider: Optional[str] = None
    ) -> list[LLMUsageLog]:
        """查询最近的调用记录。"""
        with SqlSession(self._engine) as session:
            stmt = select(LLMUsageLog).order_by(LLMUsageLog.id.desc()).limit(limit)
            if provider:
                stmt = stmt.where(LLMUsageLog.provider == provider)
            return list(session.exec(stmt))

    def get_summary(self, hours: int = 24) -> dict:
        """聚合统计：总调用次数、平均耗时、总 token 数等。"""
        from sqlalchemy import func

        with SqlSession(self._engine) as session:
            total = session.exec(select(func.count()).select_from(LLMUsageLog)).one()
            success_count = session.exec(
                select(func.count()).select_from(LLMUsageLog).where(LLMUsageLog.success)
            ).one()
            avg_duration = session.exec(
                select(func.avg(LLMUsageLog.duration_ms)).select_from(LLMUsageLog)
            ).one()
            total_tokens = session.exec(
                select(func.sum(LLMUsageLog.total_tokens)).select_from(LLMUsageLog)
            ).one()
            return {
                "total_calls": total,
                "success_rate": round(success_count / total * 100, 1) if total else 0,
                "avg_duration_ms": round(avg_duration, 1) if avg_duration else 0,
                "total_tokens": total_tokens or 0,
                "hours": hours,
            }


# ======================================================================
# 错误日志
# ======================================================================


class ErrorLogger:
    """LLM 错误日志 — 追加写入 JSONL 文件。

    所有失败的请求记录到 data/logs/llm_errors.jsonl，
    包含时间戳、供应商、模型、错误类型和详细信息。
    """

    def __init__(self, log_dir: str = "") -> None:
        self._log_dir = Path(log_dir) if log_dir else project_root / "data" / "logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("ErrorLogger 初始化完成: dir=%s", self._log_dir)

    def log_error(
        self,
        provider: str,
        model: str,
        error: Exception,
        duration_ms: float = 0.0,
    ) -> None:
        """追加一条结构化错误日志到 JSONL 文件。"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "model": model,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "duration_ms": round(duration_ms, 1),
        }
        log_file = self._log_dir / "llm_errors.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.debug(
            "错误已记录: provider=%s, model=%s, error=%s",
            provider,
            model,
            type(error).__name__,
        )


# ======================================================================
# 模块级单例
# ======================================================================

usage_tracker = UsageTracker()
error_logger = ErrorLogger()
