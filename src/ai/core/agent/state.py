"""Agent 图状态定义。"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    """LangGraph StateGraph 状态。

    Attributes:
        messages: 消息列表，使用 add_messages reducer 自动追加。
        iteration: 当前迭代次数。
        max_iterations: 最大迭代次数。
        total_tokens: 累计 token 使用量。
        session_id: 会话 ID。
        is_plan_mode: 是否处于计划模式。
        plan: 计划内容（退出计划模式时设置）。
        error: 错误信息（出错时设置）。
        checkpoint_id: 当前 checkpoint ID（断点续传）。
        interrupted_at: 中断时的节点名称（断点续传）。
        user_approval_pending: 是否等待用户审批（断点续传）。
        context_sources: 上下文来源摘要。
        reflection_count: 当前反思轮次。
        max_reflections: 最大反思轮次。
        needs_reflection: 是否需要继续反思。
        reflection_history: 反思评估历史。
        recovery_history: 工具错误恢复历史。
    """

    messages: Annotated[list[BaseMessage], add_messages]
    iteration: int
    max_iterations: int
    total_tokens: int
    session_id: str
    is_plan_mode: bool
    plan: str | None
    error: str | None
    checkpoint_id: str | None
    interrupted_at: str | None
    user_approval_pending: bool
    context_sources: list[dict]
    # 自我反思扩展字段
    reflection_count: int
    max_reflections: int
    needs_reflection: bool
    reflection_history: list[dict]
    # 错误恢复扩展字段
    recovery_history: list[dict]
