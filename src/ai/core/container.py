"""依赖注入容器 — 所有实例的唯一来源。

AppContainer 组合各模块子容器，测试时可通过
``container.xxx.override(mock_obj)`` 替换任意 Provider。
"""

from dependency_injector import containers, providers

from src.ai.core.agent.container import AgentContainer
from src.ai.core.context.container import ContextContainer
from src.ai.core.mcp.container import MCPContainer
from src.ai.core.memory.container import MemoryContainer
from src.ai.core.models.container import ModelContainer
from src.ai.core.prompts.container import PromptContainer
from src.ai.core.rag.container import RagContainer
from src.ai.core.scheduler.container import SchedulerContainer
from src.ai.core.skills.container import SkillContainer
from src.ai.core.tools.container import ToolContainer
from src.ai.storage.container import StorageContainer
from src.ai.utils.http.container import HTTPContainer


# ── 工厂函数（延迟导入，避免循环依赖和 import 时副作用） ─────────


def _create_bootstrap_settings():
    """启动期最小配置。"""
    from src.ai.config.base_config import BootstrapSettings

    return BootstrapSettings()


def _create_settings():
    """全局配置。"""
    from src.ai.config.settings import Settings

    return Settings()


def _create_chat_llm(model_service):
    """通过 ModelService 门面构建 Chat LLM 实例。"""
    return model_service.get_chat_llm()


# ── 容器定义 ─────────────────────────────────────────────────────


class AppContainer(containers.DeclarativeContainer):
    """应用级 DI 容器。

    组合各模块子容器，按依赖层级组织：
    - Layer 0: 配置（无依赖）
    - Layer 1: 基础设施（注册表、LLM 实例）
    - Layer 2: 子容器（服务）
    - Layer 3: 跨容器依赖
    """

    # ── Layer 0: 配置 ──
    bootstrap_settings = providers.Singleton(_create_bootstrap_settings)
    settings = providers.Singleton(_create_settings)

    # ── Layer 1: 基础设施 ──
    model_container = providers.Container(ModelContainer)
    chat_llm = providers.Singleton(
        _create_chat_llm,
        model_service=model_container.model_service,
    )

    # ── Layer 2: 子容器 ──
    storage_container = providers.Container(
        StorageContainer,
        bootstrap_settings=bootstrap_settings,
    )
    prompt_container = providers.Container(
        PromptContainer,
        store=storage_container.db_prompt_store,
    )
    skill_container = providers.Container(SkillContainer)
    mcp_container = providers.Container(MCPContainer)
    http_container = providers.Container(HTTPContainer)
    tool_container = providers.Container(
        ToolContainer,
        http_aclient=http_container.http_aclient,
        model_service=model_container.model_service,
    )

    memory_container = providers.Container(
        MemoryContainer,
        settings=settings,
        llm=chat_llm,
        prompt_service=prompt_container.prompt_service,
    )
    rag_container = providers.Container(
        RagContainer,
        model_service=model_container.model_service,
        settings=settings,
        prompt_service=prompt_container.prompt_service,
    )
    scheduler_container = providers.Container(
        SchedulerContainer,
        settings=settings,
        session_factory=storage_container.session_factory,
        tool_manager=tool_container.tool_manager,
        llm=chat_llm,
    )
    context_container = providers.Container(
        ContextContainer,
        settings=settings,
        memory_service=memory_container.memory_service,
        tool_registry=tool_container.tool_registry,
        prompt_service=prompt_container.prompt_service,
        llm=chat_llm,
        rag_service=rag_container.rag_service,
        file_store=memory_container.file_store,
        mcp_manager=mcp_container.mcp_manager,
        skill_service=skill_container.skill_service,
    )

    # ── Layer 3: Agent ──
    agent_container = providers.Container(
        AgentContainer,
        model_service=model_container.model_service,
        tool_manager=tool_container.tool_manager,
        context_service=context_container.context_service,
        tool_registry=tool_container.tool_registry,
    )


# 模块级容器实例
container = AppContainer()
