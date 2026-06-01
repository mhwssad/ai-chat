"""Agent 子系统 — 基于 LangGraph StateGraph 的自主任务执行。

核心组件：
- AgentOrchestrator: 编排 ReAct 循环（推理 → 工具调用 → 观察）
- GraphState: LangGraph 图状态定义
- AgentResult / AgentStatus: 执行结果类型
"""

from src.ai.core.agent.orchestrator import AgentOrchestrator
from src.ai.core.agent.types import AgentResult, AgentStatus


# 惰性导入：DI 容器单例
def __getattr__(name: str):
    if name == "agent_orchestrator":
        from src.ai.core.container import container

        return container.agent_container.agent_orchestrator()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AgentOrchestrator",
    "AgentResult",
    "AgentStatus",
    "agent_orchestrator",
]
