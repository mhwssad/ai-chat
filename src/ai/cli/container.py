"""CLI/TUI 子系统 DI 容器。"""

from __future__ import annotations

from typing import Any

from dependency_injector import containers, providers

from src.ai.cli.command_router import CommandRouter
from src.ai.cli.dashboard import Dashboard
from src.ai.cli.sessions import SessionManager
from src.ai.cli.tabs.agent_tab import AgentTab
from src.ai.cli.tabs.chat_tab import ChatTab
from src.ai.cli.tabs.image_tab import ImageTab
from src.ai.cli.tabs.memory_tab import MemoryTab
from src.ai.cli.tabs.rag_tab import RagTab
from src.ai.cli.tabs.scheduler_tab import SchedulerTab
from src.ai.cli.tabs.stats_tab import StatsTab
from src.ai.cli.tabs.system_tab import SystemTab
from src.ai.cli.tabs.tools_tab import ToolsTab
from src.ai.cli.tabs.tts_tab import TTSTab


class CLIContainer(containers.DeclarativeContainer):
    """CLI/TUI 子系统容器。"""

    chat_history_manager: Any = providers.Dependency()
    chat_service: Any = providers.Dependency()
    tool_service: Any = providers.Dependency()
    memory_service: Any = providers.Dependency()
    scheduler_service: Any = providers.Dependency()
    rag_service: Any = providers.Dependency()
    system_service: Any = providers.Dependency()
    agent_orchestrator: Any = providers.Dependency()
    image_service: Any = providers.Dependency()
    tts_service: Any = providers.Dependency()
    thread_pool: Any = providers.Dependency()
    session_factory: Any = providers.Dependency()

    session_manager = providers.Singleton(SessionManager, history_mgr=chat_history_manager)

    command_router = providers.Singleton(CommandRouter)

    chat_tab = providers.Singleton(
        ChatTab,
        thread_pool=thread_pool,
        session_mgr=session_manager,
    )
    agent_tab = providers.Singleton(
        AgentTab,
        thread_pool=thread_pool,
        agent_orchestrator=agent_orchestrator,
        session_mgr=session_manager,
    )
    tools_tab = providers.Singleton(
        ToolsTab,
        thread_pool=thread_pool,
        tool_service=tool_service,
    )
    memory_tab = providers.Singleton(
        MemoryTab,
        thread_pool=thread_pool,
        memory_service=memory_service,
    )
    scheduler_tab = providers.Singleton(
        SchedulerTab,
        thread_pool=thread_pool,
        scheduler_service=scheduler_service,
    )
    rag_tab = providers.Singleton(
        RagTab,
        thread_pool=thread_pool,
        rag_service=rag_service,
        session_mgr=session_manager,
    )
    stats_tab = providers.Singleton(
        StatsTab,
        thread_pool=thread_pool,
        session_factory=session_factory,
        memory_service=memory_service,
        system_service=system_service,
    )
    image_tab = providers.Singleton(
        ImageTab,
        thread_pool=thread_pool,
        image_service=image_service,
    )
    tts_tab = providers.Singleton(
        TTSTab,
        thread_pool=thread_pool,
        tts_service=tts_service,
    )
    system_tab = providers.Singleton(
        SystemTab,
        thread_pool=thread_pool,
        system_service=system_service,
    )

    tabs = providers.List(
        chat_tab,
        agent_tab,
        tools_tab,
        memory_tab,
        scheduler_tab,
        rag_tab,
        stats_tab,
        image_tab,
        tts_tab,
        system_tab,
    )

    dashboard = providers.Singleton(
        Dashboard,
        session_mgr=session_manager,
        tabs=tabs,
        command_router=command_router,
        thread_pool=thread_pool,
        chat_service=chat_service,
        system_service=system_service,
    )
