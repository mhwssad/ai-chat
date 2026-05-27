"""文件系统对话历史存储 — JSONL 格式持久化对话记录。"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from src.ai.utils.obj import Obj
from src.ai.utils.strings import StringUtils

logger = logging.getLogger(__name__)

_MSG_TYPE_MAP: dict[str, type[BaseMessage]] = {
    "human": HumanMessage,
    "ai": AIMessage,
    "system": SystemMessage,
    "tool": ToolMessage,
}


class FileHistoryStore:
    """基于文件系统的对话历史存储。

    每个会话对应一个目录：
        {base_dir}/sessions/{session_id}/
            history.jsonl    — 对话消息（每行一条 JSON）
            summary.json     — 压缩摘要元数据
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def _session_dir(self, session_id: str) -> Path:
        """获取会话目录路径。"""
        return self._base_dir / "sessions" / session_id

    def _history_path(self, session_id: str) -> Path:
        """获取历史文件路径。"""
        return self._session_dir(session_id) / "history.jsonl"

    def _summary_path(self, session_id: str) -> Path:
        """获取摘要文件路径。"""
        return self._session_dir(session_id) / "summary.json"

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
        """清空会话历史。"""
        path = self._history_path(session_id)
        if path.exists():
            path.unlink()

    # ── 摘要持久化 ──────────────────────────────────────

    def save_summary(
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

    def read_summary(self, session_id: str) -> dict[str, Any] | None:
        """读取压缩摘要。"""
        path = self._summary_path(session_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    # ── 内部工具 ────────────────────────────────────────

    @staticmethod
    def _count_lines(path: Path) -> int:
        """统计文件行数。"""
        if not path.exists():
            return 0
        with path.open("r", encoding="utf-8") as f:
            return sum(1 for _ in f)

    @staticmethod
    def _message_type_name(message: BaseMessage) -> str:
        """获取消息类型名称。"""
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
        """将 JSON 记录转换为 LangChain 消息。"""
        msg_type = record.get("type", "")
        cls = _MSG_TYPE_MAP.get(msg_type)
        if cls is None:
            return None
        return cls(content=record.get("content", ""))

    @staticmethod
    def format_file_references(
        file_refs: list[dict[str, Any]], max_show: int = 20
    ) -> str:
        """格式化文件引用提示。"""
        if not file_refs:
            return ""
        lines = ["### 可回读的原始消息位置", ""]
        for ref in file_refs[:max_show]:
            idx = ref.get("index", "?")
            snippet = StringUtils.truncate(ref.get("snippet", ""), length=50)
            lines.append(f"- 消息#{idx}: {snippet}")
        return "\n".join(lines)
