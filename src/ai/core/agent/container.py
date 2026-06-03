"""Agent 子系统 DI 容器。"""

from typing import Any

from dependency_injector import containers, providers


def _create_agent_orchestrator(
    model_service, tool_manager, context_service, tool_registry, checkpointer=None
):
    """构建 AgentOrchestrator。"""
    from src.ai.core.agent.orchestrator import AgentOrchestrator

    return AgentOrchestrator(
        model_service=model_service,
        tool_manager=tool_manager,
        context_service=context_service,
        tool_registry=tool_registry,
        checkpointer=checkpointer,
    )


def _create_checkpointer():
    """创建 AsyncSqliteSaver（复用项目 SQLite）。"""
    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver  # type: ignore[import-not-found]

        return AsyncSqliteSaver()
    except ImportError:
        # langgraph checkpoint sqlite 不可用时返回 None
        return None


class AgentContainer(containers.DeclarativeContainer):
    """Agent 子系统容器。"""

    # 外部依赖
    model_service: Any = providers.Dependency()
    tool_manager: Any = providers.Dependency()
    context_service: Any = providers.Dependency()
    tool_registry: Any = providers.Dependency()

    # Checkpointer（可选）
    checkpointer = providers.Singleton(_create_checkpointer)

    agent_orchestrator = providers.Singleton(
        _create_agent_orchestrator,
        model_service=model_service,
        tool_manager=tool_manager,
        context_service=context_service,
        tool_registry=tool_registry,
        checkpointer=checkpointer,
    )
