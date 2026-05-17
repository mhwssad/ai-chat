"""工作流引擎 — 将声明式配置编译为 LangGraph StateGraph。"""

from __future__ import annotations

from typing import Optional

from langgraph.graph import END, START, StateGraph

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.workflows.models import (
    WorkflowRecord,
)
from src.ai_chat.workflows.nodes import NodeExecutorFactory
from src.ai_chat.workflows.state import WorkflowState

logger = get_logger(__name__)


class WorkflowEngineError(Exception):
    """工作流引擎编译或执行异常。"""


def validate_workflow(record: WorkflowRecord) -> list[str]:
    """校验工作流配置，返回错误消息列表（空列表表示通过）。"""
    errors: list[str] = []
    nodes = record.nodes
    edges = record.edges
    node_names = {n.name for n in nodes}

    # 节点基本检查
    if not nodes:
        errors.append("工作流至少需要一个节点")
        return errors

    input_nodes = [n for n in nodes if n.type == "input"]
    output_nodes = [n for n in nodes if n.type == "output"]

    if len(input_nodes) != 1:
        errors.append(f"需要恰好 1 个 input 节点，当前 {len(input_nodes)} 个")
    if not output_nodes:
        errors.append("至少需要 1 个 output 节点")

    # 边引用检查
    for edge in edges:
        if edge.source not in node_names and edge.source not in {n.name for n in output_nodes}:
            errors.append(f"边源节点 '{edge.source}' 不存在于节点列表中")
        if edge.type == "direct" and edge.target and edge.target not in node_names:
            errors.append(f"边目标节点 '{edge.target}' 不存在于节点列表中")
        if edge.type == "conditional":
            for key, target in edge.conditions.items():
                if target not in node_names:
                    errors.append(f"条件边目标 '{target}' 不存在于节点列表中")

    # classifier 必须有 conditional 边
    classifiers = {n.name for n in nodes if n.type == "classifier"}
    conditional_sources = {e.source for e in edges if e.type == "conditional"}
    for cls_name in classifiers:
        if cls_name not in conditional_sources:
            errors.append(f"classifier 节点 '{cls_name}' 必须后接 conditional 边")

    # chain/agent 节点必须有 ref
    for n in nodes:
        if n.type in ("chain", "agent") and not n.ref:
            errors.append(f"{n.type} 节点 '{n.name}' 缺少 ref 字段")

    return errors


class WorkflowEngine:
    """工作流引擎 — 将 WorkflowRecord 编译为可执行的 LangGraph。"""

    def __init__(self, node_factory: Optional[NodeExecutorFactory] = None) -> None:
        self._node_factory = node_factory or NodeExecutorFactory()

    def compile(self, record: WorkflowRecord):
        """将 WorkflowRecord 编译为可执行的 LangGraph。"""
        errors = validate_workflow(record)
        if errors:
            raise WorkflowEngineError(f"工作流校验失败: {'; '.join(errors)}")

        nodes = record.nodes
        edges = record.edges
        wf_config = record.config
        workflow = StateGraph(WorkflowState)

        # 找到入口/出口虚拟节点
        exit_names = {n.name for n in nodes if n.type == "output"}
        entry_node = next((n for n in nodes if n.type == "input"), None)

        # 注册所有非虚拟节点
        for node in nodes:
            if node.type in ("input", "output"):
                continue
            node_fn = self._node_factory.build(node, wf_config)
            workflow.add_node(node.name, node_fn)

        # START → input 的 direct 边目标
        handled_entry_edge = False
        if entry_node:
            entry_edges = [e for e in edges if e.source == entry_node.name and e.type == "direct"]
            if entry_edges:
                target = entry_edges[0].target
                if target not in exit_names:
                    workflow.add_edge(START, target)
                handled_entry_edge = True

        # 注册所有边
        nodes_with_outgoing: set[str] = set()
        for edge in edges:
            # 跳过 input 出边（已处理）和 output 出边
            if entry_node and edge.source == entry_node.name and edge.type == "direct" and handled_entry_edge:
                continue
            if edge.source in exit_names:
                continue

            nodes_with_outgoing.add(edge.source)

            if edge.type == "direct":
                target = edge.target
                if target in exit_names:
                    workflow.add_edge(edge.source, END)
                else:
                    workflow.add_edge(edge.source, target)

            elif edge.type == "conditional":
                resolved = {}
                for key, target in edge.conditions.items():
                    resolved[key] = END if target in exit_names else target
                router = _make_router(resolved)
                workflow.add_conditional_edges(edge.source, router, resolved)

        # 兜底：无出边的节点连 END
        for node in nodes:
            if node.type in ("input", "output"):
                continue
            if node.name not in nodes_with_outgoing:
                workflow.add_edge(node.name, END)

        return workflow.compile()


def _make_router(mapping: dict[str, str]):
    """创建条件路由函数。"""
    def router(state: WorkflowState) -> str:
        intent = state.get("intent", "")
        target = mapping.get(intent)
        if target is None:
            first_value = next(iter(mapping.values()), END)
            return first_value
        return target
    return router
