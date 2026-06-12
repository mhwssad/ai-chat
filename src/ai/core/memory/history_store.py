"""文件系统对话历史存储。

职责分离：
- FileMessageStore: JSONL 格式的对话消息读写
- FileSummaryStore: JSON 格式的压缩摘要读写
- FileHistoryStore: 组合门面，对外保持统一接口

存储结构：
{base_dir}/sessions/{session_id}/
    history.jsonl    — 对话消息（每行一条 JSON）
    summary.json     — 压缩摘要元数据
"""

from __future__ import annotations

import json
from src.ai.config.logging_setup import get_logger
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.ai.utils.obj import Obj

if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage

logger = get_logger(__name__)


def _get_msg_type_map() -> dict[str, type[BaseMessage]]:
    """延迟加载消息类型映射。"""
    from langchain_core.messages import (
        AIMessage,
        HumanMessage,
        SystemMessage,
        ToolMessage,
    )

    return {
        "human": HumanMessage,
        "ai": AIMessage,
        "system": SystemMessage,
        "tool": ToolMessage,
    }


class FileMessageStore:
    """JSONL 格式的对话消息存储。

    每条消息序列化为一行 JSON，追加写入 history.jsonl。
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def _session_dir(self, session_id: str) -> Path:
        return self._base_dir / "sessions" / session_id

    def _history_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "history.jsonl"

    def append_message(self, session_id: str, message: BaseMessage) -> None:
        """追加一条消息到 JSONL 文件。"""
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        path = self._history_path(session_id)
        index = self._count_lines(path)

        record = {
            "type": self._message_type_name(message),
            "content": Obj.safe_content_str(message),
            "timestamp": datetime.now().isoformat(),
            "index": index,
            "metadata": getattr(message, "additional_kwargs", {}),
        }
        tool_call_id = getattr(message, "tool_call_id", None)
        if tool_call_id:
            record["tool_call_id"] = tool_call_id

        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_messages(
        self,
        session_id: str,
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[BaseMessage]:
        """从 JSONL 文件读取消息。"""
        path = self._history_path(session_id)
        if not path.exists():
            return []

        messages: list[BaseMessage] = []
        with path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i < offset:
                    continue
                if limit is not None and len(messages) >= limit:
                    break
                record = json.loads(line.strip())
                msg = self._record_to_message(record)
                if msg is not None:
                    messages.append(msg)
        return messages

    def read_records(
        self,
        session_id: str,
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """读取原始记录（含 index/timestamp），供压缩策略生成文件引用。"""
        path = self._history_path(session_id)
        if not path.exists():
            return []

        records: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i < offset:
                    continue
                if limit is not None and len(records) >= limit:
                    break
                records.append(json.loads(line.strip()))
        return records

    def message_count(self, session_id: str) -> int:
        """获取会话消息总数。"""
        return self._count_lines(self._history_path(session_id))

    def clear(self, session_id: str) -> None:
        """清空会话消息历史。"""
        path = self._history_path(session_id)
        if path.exists():
            path.unlink()

    # ── 内部工具 ────────────────────────────────────────

    @staticmethod
    def _count_lines(path: Path) -> int:
        if not path.exists():
            return 0
        with path.open("r", encoding="utf-8") as f:
            return sum(1 for _ in f)

    @staticmethod
    def _message_type_name(message: BaseMessage) -> str:
        from langchain_core.messages import (
            AIMessage,
            HumanMessage,
            SystemMessage,
            ToolMessage,
        )

        if isinstance(message, HumanMessage):
            return "human"
        if isinstance(message, AIMessage):
            return "ai"
        if isinstance(message, SystemMessage):
            return "system"
        if isinstance(message, ToolMessage):
            return "tool"
        return getattr(message, "type", "unknown")

    @staticmethod
    def _record_to_message(record: dict[str, Any]) -> BaseMessage | None:
        msg_type = record.get("type", "")
        cls = _get_msg_type_map().get(msg_type)
        if cls is None:
            return None
        kwargs: dict[str, Any] = {"content": record.get("content", "")}
        if msg_type == "tool":
            kwargs["tool_call_id"] = record.get("tool_call_id", "")
        return cls(**kwargs)


class FileSummaryStore:
    """JSON 格式的压缩摘要存储。

    每个会话的摘要保存为 summary.json。
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def _session_dir(self, session_id: str) -> Path:
        return self._base_dir / "sessions" / session_id

    def _summary_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "summary.json"

    def save(
        self,
        session_id: str,
        summary: str,
        *,
        compressed_range: tuple[int, int],
        file_references: list[dict[str, Any]],
    ) -> None:
        """保存压缩摘要到 JSON 文件。"""
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "summary": summary,
            "compressed_range": list(compressed_range),
            "file_references": file_references,
            "updated_at": datetime.now().isoformat(),
        }
        path = self._summary_path(session_id)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def read(self, session_id: str) -> dict[str, Any] | None:
        """读取压缩摘要。"""
        path = self._summary_path(session_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))


class FileHistoryStore:
    """基于文件系统的对话历史存储门面。

    组合 FileMessageStore 和 FileSummaryStore，
    对外保持统一接口以兼容现有调用方。
    """

    def __init__(self, base_dir: Path) -> None:
        self._messages = FileMessageStore(base_dir)
        self._summaries = FileSummaryStore(base_dir)

    @property
    def messages(self) -> FileMessageStore:
        """消息存储。"""
        return self._messages

    @property
    def summaries(self) -> FileSummaryStore:
        """摘要存储。"""
        return self._summaries

    # ── 委托给 FileMessageStore ─────────────────────────

    def append_message(self, session_id: str, message: BaseMessage) -> None:
        self._messages.append_message(session_id, message)

    def read_messages(
        self,
        session_id: str,
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[BaseMessage]:
        return self._messages.read_messages(session_id, offset=offset, limit=limit)

    def read_records(
        self,
        session_id: str,
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        return self._messages.read_records(session_id, offset=offset, limit=limit)

    def message_count(self, session_id: str) -> int:
        return self._messages.message_count(session_id)

    def clear(self, session_id: str) -> None:
        self._messages.clear(session_id)

    # ── 委托给 FileSummaryStore ─────────────────────────

    def save_summary(
        self,
        session_id: str,
        summary: str,
        *,
        compressed_range: tuple[int, int],
        file_references: list[dict[str, Any]],
    ) -> None:
        self._summaries.save(
            session_id,
            summary,
            compressed_range=compressed_range,
            file_references=file_references,
        )

    def read_summary(self, session_id: str) -> dict[str, Any] | None:
        return self._summaries.read(session_id)
