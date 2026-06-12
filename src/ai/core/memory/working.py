"""工作记忆 — 维护当前任务的中间状态、待办列表和决策记录。

职责：
1. WorkingMemory: 键值存储，Agent 可读写中间结果
2. TaskTodoList: 当前任务的子任务列表及状态
3. DecisionLog: 记录 Agent 的关键决策及理由
4. 生命周期与会话绑定，会话结束可选择持久化
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from src.ai.config.logging_setup import get_logger

logger = get_logger(__name__)


class TodoStatus(str, Enum):
    """待办事项状态。"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass
class TodoItem:
    """待办事项。"""

    id: str
    title: str
    status: TodoStatus = TodoStatus.PENDING
    description: str = ""
    result: str | None = None


@dataclass
class DecisionEntry:
    """决策记录。"""

    id: str
    decision: str  # 决策内容
    reasoning: str  # 决策理由
    alternatives: list[str] = field(default_factory=list)  # 被排除的选项
    step_index: int = 0  # 对应的执行步骤


class WorkingMemory:
    """工作记忆 — 任务级 scratchpad。

    提供三个维度的临时存储：
    - kv_store: 通用键值存储，Agent 可自由读写
    - todo_list: 任务分解后的子任务列表
    - decision_log: 关键决策记录

    生命周期与会话绑定。会话结束时可通过 `persist()` 持久化到文件。

    Args:
        session_id: 关联的会话 ID。
        persist_dir: 持久化目录（可选）。
    """

    def __init__(
        self,
        *,
        session_id: str,
        persist_dir: str | None = None,
    ) -> None:
        self._session_id = session_id
        self._persist_dir = Path(persist_dir) if persist_dir else None
        self._kv_store: dict[str, Any] = {}
        self._todo_list: list[TodoItem] = []
        self._decision_log: list[DecisionEntry] = []
        self._todo_counter = 0
        self._decision_counter = 0

    # ── 键值存储 ────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """读取键值。

        Args:
            key: 键名。
            default: 默认值。

        Returns:
            键对应的值，不存在则返回默认值。
        """
        return self._kv_store.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """写入键值。

        Args:
            key: 键名。
            value: 值。
        """
        self._kv_store[key] = value

    def has(self, key: str) -> bool:
        """检查键是否存在。"""
        return key in self._kv_store

    def delete(self, key: str) -> bool:
        """删除键值。

        Returns:
            True 表示键存在并被删除。
        """
        if key in self._kv_store:
            del self._kv_store[key]
            return True
        return False

    def keys(self) -> list[str]:
        """获取所有键名。"""
        return list(self._kv_store.keys())

    def snapshot(self) -> dict[str, Any]:
        """获取完整键值快照。"""
        return dict(self._kv_store)

    # ── 待办列表 ────────────────────────────────────────────

    def add_todo(self, title: str, description: str = "") -> TodoItem:
        """添加待办事项。

        Args:
            title: 事项标题。
            description: 详细描述。

        Returns:
            新建的待办事项。
        """
        self._todo_counter += 1
        item = TodoItem(
            id=f"todo_{self._todo_counter}",
            title=title,
            description=description,
        )
        self._todo_list.append(item)
        return item

    def update_todo(self, todo_id: str, status: TodoStatus, result: str | None = None) -> bool:
        """更新待办事项状态。

        Args:
            todo_id: 事项 ID。
            status: 新状态。
            result: 结果描述（可选）。

        Returns:
            True 表示找到并更新。
        """
        for item in self._todo_list:
            if item.id == todo_id:
                item.status = status
                if result is not None:
                    item.result = result
                return True
        return False

    def get_todos(self, status: TodoStatus | None = None) -> list[TodoItem]:
        """获取待办列表。

        Args:
            status: 按状态过滤（None 表示全部）。

        Returns:
            待办事项列表。
        """
        if status is None:
            return list(self._todo_list)
        return [t for t in self._todo_list if t.status == status]

    @property
    def todo_progress(self) -> tuple[int, int]:
        """待办进度（已完成数, 总数）。"""
        total = len(self._todo_list)
        completed = sum(1 for t in self._todo_list if t.status == TodoStatus.COMPLETED)
        return completed, total

    # ── 决策记录 ────────────────────────────────────────────

    def record_decision(
        self,
        *,
        decision: str,
        reasoning: str,
        alternatives: list[str] | None = None,
        step_index: int = 0,
    ) -> DecisionEntry:
        """记录一个决策。

        Args:
            decision: 决策内容。
            reasoning: 决策理由。
            alternatives: 被排除的选项。
            step_index: 对应的执行步骤。

        Returns:
            决策记录条目。
        """
        self._decision_counter += 1
        entry = DecisionEntry(
            id=f"decision_{self._decision_counter}",
            decision=decision,
            reasoning=reasoning,
            alternatives=alternatives or [],
            step_index=step_index,
        )
        self._decision_log.append(entry)
        return entry

    def get_decisions(self) -> list[DecisionEntry]:
        """获取所有决策记录。"""
        return list(self._decision_log)

    # ── 持久化 ──────────────────────────────────────────────

    def persist(self) -> Path | None:
        """将工作记忆持久化到文件。

        Returns:
            持久化文件路径，如果未配置 persist_dir 则返回 None。
        """
        if self._persist_dir is None:
            return None

        self._persist_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._persist_dir / f"working_memory_{self._session_id}.json"

        data = {
            "session_id": self._session_id,
            "kv_store": self._kv_store,
            "todo_list": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status.value,
                    "description": t.description,
                    "result": t.result,
                }
                for t in self._todo_list
            ],
            "decision_log": [
                {
                    "id": d.id,
                    "decision": d.decision,
                    "reasoning": d.reasoning,
                    "alternatives": d.alternatives,
                    "step_index": d.step_index,
                }
                for d in self._decision_log
            ],
        }

        file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("工作记忆已持久化: session=%s, path=%s", self._session_id, file_path)
        return file_path

    @classmethod
    def load(cls, file_path: Path) -> WorkingMemory:
        """从文件加载工作记忆。

        Args:
            file_path: 持久化文件路径。

        Returns:
            恢复的工作记忆实例。
        """
        data = json.loads(file_path.read_text(encoding="utf-8"))
        memory = cls(
            session_id=data["session_id"],
            persist_dir=str(file_path.parent),
        )

        memory._kv_store = data.get("kv_store", {})

        for t in data.get("todo_list", []):
            memory._todo_list.append(
                TodoItem(
                    id=t["id"],
                    title=t["title"],
                    status=TodoStatus(t.get("status", "pending")),
                    description=t.get("description", ""),
                    result=t.get("result"),
                )
            )
            memory._todo_counter = max(
                memory._todo_counter, int(t["id"].split("_")[-1])
            )

        for d in data.get("decision_log", []):
            memory._decision_log.append(
                DecisionEntry(
                    id=d["id"],
                    decision=d["decision"],
                    reasoning=d["reasoning"],
                    alternatives=d.get("alternatives", []),
                    step_index=d.get("step_index", 0),
                )
            )
            memory._decision_counter = max(
                memory._decision_counter, int(d["id"].split("_")[-1])
            )

        return memory

    # ── 状态摘要 ────────────────────────────────────────────

    def to_context_text(self) -> str:
        """生成可注入到 LLM 上下文的工作记忆摘要。"""
        parts: list[str] = []

        if self._kv_store:
            parts.append("【中间结果】")
            for key, value in self._kv_store.items():
                value_str = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
                parts.append(f"  {key}: {value_str[:200]}")

        if self._todo_list:
            completed, total = self.todo_progress
            parts.append(f"\n【任务进度】{completed}/{total}")
            for t in self._todo_list:
                status_icon = {"pending": "⬜", "in_progress": "🔄", "completed": "✅", "skipped": "⏭️"}.get(t.status.value, "⬜")
                parts.append(f"  {status_icon} {t.title}")

        if self._decision_log:
            parts.append("\n【关键决策】")
            for d in self._decision_log:
                parts.append(f"  - {d.decision}: {d.reasoning}")

        return "\n".join(parts) if parts else ""

    def clear(self) -> None:
        """清空所有工作记忆。"""
        self._kv_store.clear()
        self._todo_list.clear()
        self._decision_log.clear()
        self._todo_counter = 0
        self._decision_counter = 0
