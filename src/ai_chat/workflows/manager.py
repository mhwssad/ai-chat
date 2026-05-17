"""工作流管理器 — 持久化配置与运行时编译/执行的桥梁。"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.workflows.engine import WorkflowEngine
from src.ai_chat.workflows.models import (
    EdgeConfig,
    NodeConfig,
    WorkflowConfig,
    WorkflowCreateRequest,
    WorkflowRecord,
)
from src.ai_chat.workflows.store import WorkflowStore

logger = get_logger(__name__)


class WorkflowManager:
    """工作流配置管理器 — CRUD + 运行时编译/执行。"""

    def __init__(self, store: Optional[WorkflowStore] = None) -> None:
        self._store = store or WorkflowStore()
        self._engine = WorkflowEngine()

    # ── CRUD ──────────────────────────────────────────

    def create_workflow(
        self,
        name: str,
        description: str = "",
        model_name: str = "",
        nodes: Optional[list[NodeConfig]] = None,
        edges: Optional[list[EdgeConfig]] = None,
        config: Optional[WorkflowConfig] = None,
        tags: str = "",
    ) -> WorkflowRecord:
        """创建工作流配置。"""
        request = WorkflowCreateRequest(
            name=name,
            description=description,
            model_name=model_name,
            nodes=nodes or [],
            edges=edges or [],
            config=config or WorkflowConfig(),
            tags=tags,
        )
        record = self._store.create(request)
        logger.info("创建工作流: %s (%d 节点, %d 边)", name, len(nodes or []), len(edges or []))
        return record

    def get_workflow(self, name: str) -> WorkflowRecord:
        return self._store.get(name)

    def update_workflow(self, name: str, **fields) -> WorkflowRecord:
        return self._store.update(name, **fields)

    def delete_workflow(self, name: str) -> None:
        self._store.delete(name)
        logger.info("删除工作流: %s", name)

    def list_workflows(self, limit: int = 50, offset: int = 0) -> list[WorkflowRecord]:
        return self._store.list(limit=limit, offset=offset)

    def search_workflows(self, keyword: str, limit: int = 50) -> list[WorkflowRecord]:
        return self._store.search(keyword, limit=limit)

    def workflow_exists(self, name: str) -> bool:
        return self._store.exists(name)

    def count_workflows(self) -> int:
        return self._store.count()

    # ── 执行 ──────────────────────────────────────────

    def invoke(self, name: str, message: str, **kwargs) -> str:
        """编译并执行工作流。"""
        record = self.get_workflow(name)
        graph = self._engine.compile(record)
        result = graph.invoke({
            "messages": [HumanMessage(content=message)],
            "intent": "",
            "context": "",
            "outputs": {},
            "metadata": kwargs,
        })
        ai_msg = result["messages"][-1]
        content = ai_msg.content if isinstance(ai_msg, AIMessage) else str(ai_msg.content)
        return content

    def stream(self, name: str, message: str, **kwargs) -> Iterator[str]:
        """流式执行工作流。"""
        record = self.get_workflow(name)
        graph = self._engine.compile(record)
        seen_ids: set[str] = set()
        for event in graph.stream(
            {
                "messages": [HumanMessage(content=message)],
                "intent": "",
                "context": "",
                "outputs": {},
                "metadata": kwargs,
            },
            stream_mode="values",
        ):
            if not event.get("messages"):
                continue
            last = event["messages"][-1]
            if (
                isinstance(last, AIMessage)
                and isinstance(last.content, str)
                and last.content
                and last.id not in seen_ids
            ):
                seen_ids.add(last.id)
                yield last.content


# 全局单例
workflow_manager = WorkflowManager()
