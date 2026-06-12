"""依赖注入容器 — 所有实例的唯一来源。

AppContainer 组合各模块子容器，测试时可通过
``container.xxx.override(mock_obj)`` 替换任意 Provider。

配置通过统一的 ConfigContainer 管理，支持热更新和生命周期控制。
"""

from dependency_injector import containers, providers

from src.ai.config.container import config as config_container
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
from src.ai.service.container import ServiceContainer
from src.ai.storage.container import StorageContainer
from src.ai.utils.http.container import HTTPContainer


# -- 工厂函数（延迟导入，避免循环依赖和 import 时副作用） --


def _create_chat_llm(model_service):
    """通过 ModelService 门面构建 Chat LLM 实例。"""
    return model_service.get_chat_llm()


def _create_thread_pool(settings):
    """创建并启动统一线程池。"""
    from src.ai.utils.thread_pool import ThreadPoolManager

    tp_settings = settings.thread_pool
    mgr = ThreadPoolManager(
        io_size=tp_settings.io_size,
        cpu_size=tp_settings.cpu_size,
        bg_size=tp_settings.bg_size,
        shutdown_timeout=tp_settings.shutdown_timeout,
    )
    mgr.start()
    return mgr


# ── 容器定义 ─────────────────────────────────────────────────────


class AppContainer(containers.DeclarativeContainer):
    """应用级 DI 容器。

    组合各模块子容器，按依赖层级组织：
    - Layer 0: 配置（无依赖）
    - Layer 1: 基础设施（线程池、注册表、LLM 实例）
    - Layer 2: 子容器（服务）
    - Layer 3: 跨容器依赖

    注意：不使用 wiring_config 自动 wire。因为 container = AppContainer()
    在模块顶层执行，自动 wire 会在路由模块尚未完全加载时触发，导致 wire 不完整。
    所有 wiring 通过 container_wiring.initialize_container() 在 lifespan
    阶段显式完成（此时所有模块已加载完毕）。
    """

    # -- Layer 0: 配置（委托给统一 ConfigContainer） --
    bootstrap_settings = providers.Callable(lambda: config_container.bootstrap_settings)
    settings = providers.Callable(lambda: config_container.settings)
    chat_model_config = providers.Callable(lambda: config_container.chat_model_config)

    # -- Layer 1: 基础设施 --
    thread_pool = providers.Singleton(_create_thread_pool, settings=settings)
    model_container = providers.Container(ModelContainer)
    chat_llm = providers.Singleton(
        _create_chat_llm,
        model_service=model_container.model_service,
    )

    # -- Layer 2: 子容器 --
    storage_container = providers.Container(
        StorageContainer,
        bootstrap_settings=bootstrap_settings,
    )
    prompt_container = providers.Container(
        PromptContainer,
        store=storage_container.db_prompt_store,
    )
    skill_container = providers.Container(
        SkillContainer,
    )
    mcp_container = providers.Container(
        MCPContainer,
        session_factory=storage_container.session_factory,
    )
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
        thread_pool=thread_pool,
        session_factory=storage_container.session_factory,
    )
    rag_container = providers.Container(
        RagContainer,
        model_service=model_container.model_service,
        settings=settings,
        prompt_service=prompt_container.prompt_service,
        thread_pool=thread_pool,
        session_factory=storage_container.session_factory,
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
        chat_model_config=chat_model_config,
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

    # ── Layer 4: 共享服务 ──
    service_container = providers.Container(
        ServiceContainer,
        model_service=model_container.model_service,
        context_service=context_container.context_service,
        tool_manager=tool_container.tool_manager,
        tool_registry=tool_container.tool_registry,
        memory_service=memory_container.memory_service,
        chat_history_manager=context_container.chat_history_manager,
        chat_llm=chat_llm,
        thread_pool=thread_pool,
        scheduler_service=scheduler_container.scheduler_service,
        settings=settings,
        # 新增依赖
        rag_service=rag_container.rag_service,
        prompt_service=prompt_container.prompt_service,
        agent_orchestrator=agent_container.agent_orchestrator,
        skill_service=skill_container.skill_service,
        session_factory=storage_container.session_factory,
    )


# 模块级容器实例
container = AppContainer()
