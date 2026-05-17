"""工作流状态定义 — LangGraph StateGraph 统一状态。"""

from __future__ import annotations

from typing import Any, Annotated

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class WorkflowState(TypedDict):
    """工作流引擎统一状态。

    字段说明:
    - messages: 对话消息列表（LangGraph add_messages reducer）
    - intent: 分类器节点的路由键
    - context: 上下文文本（RAG 检索结果等）
    - outputs: 各节点的输出，按节点名索引
    - metadata: 工作流级元数据（model_name, session_id 等）
    """

    messages: Annotated[list[BaseMessage], add_messages]
    intent: str
    context: str
    outputs: dict[str, Any]
    metadata: dict[str, Any]


def extract_last_human_message(messages: list[BaseMessage]) -> str:
    """从消息列表中提取最后一条 HumanMessage 的文本内容。"""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content if isinstance(msg.content, str) else str(msg.content)
    return ""
