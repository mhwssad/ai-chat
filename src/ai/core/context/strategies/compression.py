"""压缩策略 — 调度压缩时机，委托 FullCompact 执行压缩，自身负责持久化。

拆分为两个类：
- CompressionContextBuilder：上下文消息构建（无状态依赖 FileHistoryStore）
- CompressionStrategy：压缩调度 + 持久化
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.ai.core.memory.prompt import MemoryPromptBuilder

from .base import BaseMemoryStrategy

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import BaseMessage

    from src.ai.core.context.compact import FullCompact
    from src.ai.core.memory.history import ChatHistoryManager
    from src.ai.core.memory.history_store import FileHistoryStore

logger = logging.getLogger(__name__)


class CompressionContextBuilder:
    """上下文消息构建器。

    职责：
    - 从 FileHistoryStore 读取摘要和最近消息
    - 组装为 LLM 可用的上下文消息列表

    与 CompressionStrategy 分离，使上下文构建逻辑独立可测试。
    """

    def __init__(self, file_store: FileHistoryStore, keep_recent: int = 10) -> None:
        self._file_store = file_store
        self._keep_recent = keep_recent

    def build_messages(
        self,
        session_id: str | None,
        system_prompt: str,
    ) -> list[BaseMessage]:
        """构建上下文消息列表。

        Args:
            session_id: 会话 ID。
            system_prompt: 系统提示词。

        Returns:
            上下文消息列表。
        """
        from langchain_core.messages import SystemMessage

        result: list[BaseMessage] = []
        if system_prompt:
            result.append(SystemMessage(content=system_prompt))

        if session_id:
            self._inject_summary(result, session_id)
            total = self._file_store.message_count(session_id)
            offset = max(0, total - self._keep_recent)
            recent = self._file_store.read_messages(session_id, offset=offset)
            result.extend(recent)

        return result

    def _inject_summary(self, result: list[BaseMessage], session_id: str) -> None:
        """读取摘要并注入为系统消息。"""
        from langchain_core.messages import SystemMessage

        summary_data = self._file_store.read_summary(session_id)
        if not summary_data:
            return

        ref_text = MemoryPromptBuilder.format_file_references(
            summary_data.get("file_references", [])
        )
        summary_content = f"## 之前的对话摘要\n\n{summary_data.get('summary', '')}"
        if ref_text:
            summary_content += f"\n\n{ref_text}"
        result.append(SystemMessage(content=summary_content))


class CompressionStrategy(BaseMemoryStrategy):
    """压缩策略。

    职责：
    - 判断何时触发压缩（消息数阈值）
    - 选择压缩模式（增量 / 全量）
    - 从 FileHistoryStore 读取待压缩记录
    - 将压缩结果保存到 FileHistoryStore

    压缩算法由 FullCompact（context 模块）提供。
    上下文消息构建委托给 CompressionContextBuilder。
    """

    def __init__(
        self,
        history_manager: ChatHistoryManager,
        file_store: FileHistoryStore,
        llm: BaseChatModel,
        prompt_service: object,
        *,
        max_messages: int = 30,
        keep_recent: int = 10,
        full_compact_threshold: int = 100,
    ) -> None:
        super().__init__(history_manager)
        self._file_store = file_store
        self._max_messages = max_messages
        self._keep_recent = keep_recent
        self._full_compact_threshold = full_compact_threshold

        from src.ai.core.context.compact import FullCompact

        self._full_compact: FullCompact = FullCompact(
            llm, prompt_service=prompt_service, keep_recent=keep_recent
        )
        self._context_builder = CompressionContextBuilder(
            file_store=file_store, keep_recent=keep_recent
        )

    @property
    def strategy_name(self) -> str:
        return "compression"

    # ── 上下文消息构建（委托给 builder） ────────────────────

    def build_context_messages(
        self,
        session_id: str | None,
        system_prompt: str,
        *,
        max_tokens: int | None = None,
    ) -> list[BaseMessage]:
        """构建上下文消息列表（同步）。"""
        return self._context_builder.build_messages(session_id, system_prompt)

    async def abuild_context_messages(
        self,
        session_id: str | None,
        system_prompt: str,
        *,
        max_tokens: int | None = None,
    ) -> list[BaseMessage]:
        """构建上下文消息列表（异步，含自动压缩）。"""
        if session_id:
            total = self._file_store.message_count(session_id)
            if total > self._max_messages:
                await self._acompress(session_id)

        return self._context_builder.build_messages(session_id, system_prompt)

    # ── 消息写入 ──────────────────────────────────────────

    def add_message(self, session_id: str, message: BaseMessage) -> None:
        """添加消息到历史记录。"""
        self._history.add_message(session_id, message)

    async def aadd_message(self, session_id: str, message: BaseMessage) -> None:
        """添加消息到历史记录（异步）。"""
        self.add_message(session_id, message)

    # ── 压缩调度 ──────────────────────────────────────────

    async def _acompress(self, session_id: str) -> None:
        """根据消息数量选择压缩模式。"""
        total = self._file_store.message_count(session_id)

        if total > self._full_compact_threshold:
            await self._afull_compact(session_id, total=total)
        else:
            await self._aincremental_compress(session_id, total=total)

    async def _aincremental_compress(
        self, session_id: str, *, total: int | None = None
    ) -> None:
        """增量压缩：委托 FullCompact，自身负责读取和持久化。"""
        summary_data = self._file_store.read_summary(session_id)
        existing_summary = summary_data.get("summary", "") if summary_data else ""
        existing_end = (
            summary_data.get("compressed_range", [0, 0])[1] if summary_data else 0
        )

        if total is None:
            total = self._file_store.message_count(session_id)
        compress_end = total - self._keep_recent

        if compress_end <= existing_end:
            return

        records = self._file_store.read_records(
            session_id, offset=existing_end, limit=compress_end - existing_end
        )
        if not records:
            return

        try:
            new_summary = await self._full_compact.compact_incremental(
                records, existing_summary=existing_summary
            )

            file_refs = [
                {
                    "index": r.get("index", 0),
                    "timestamp": r.get("timestamp", ""),
                    "snippet": str(r.get("content", ""))[:80],
                }
                for r in records
            ]

            self._file_store.save_summary(
                session_id,
                new_summary,
                compressed_range=(0, compress_end),
                file_references=file_refs,
            )
            logger.info(
                "会话 %s 增量压缩完成：压缩了 %d 条消息，保留最近 %d 条",
                session_id,
                len(records),
                self._keep_recent,
            )
        except Exception:
            logger.warning("增量压缩失败，保留原始消息", exc_info=True)

    async def _afull_compact(
        self, session_id: str, *, total: int | None = None
    ) -> None:
        """全量压缩：委托 FullCompact，自身负责读取和持久化。"""
        summary_data = self._file_store.read_summary(session_id)
        existing_summary = summary_data.get("summary", "") if summary_data else ""

        if total is None:
            total = self._file_store.message_count(session_id)
        compress_end = total - self._keep_recent

        records = self._file_store.read_records(
            session_id, offset=0, limit=compress_end
        )
        if not records:
            return

        messages = [
            msg
            for r in records
            if (msg := self._file_store._record_to_message(r)) is not None
        ]
        if not messages:
            return

        try:
            new_summary, _ = await self._full_compact.compact_full(
                messages, existing_summary=existing_summary
            )

            file_refs = [
                {
                    "index": r.get("index", 0),
                    "timestamp": r.get("timestamp", ""),
                    "snippet": str(r.get("content", ""))[:80],
                }
                for r in records
            ]

            self._file_store.save_summary(
                session_id,
                new_summary,
                compressed_range=(0, compress_end),
                file_references=file_refs,
            )
            logger.info(
                "会话 %s 全量压缩完成：压缩了 %d 条消息，保留最近 %d 条",
                session_id,
                len(records),
                self._keep_recent,
            )
        except Exception:
            logger.warning("全量压缩失败，保留原始消息", exc_info=True)

    # ── 原文回读 ──────────────────────────────────────────

    def read_original(self, session_id: str, message_index: int) -> str | None:
        """根据文件引用回读原始消息内容。"""
        records = self._file_store.read_records(
            session_id, offset=message_index, limit=1
        )
        if records:
            return records[0].get("content")
        return None
