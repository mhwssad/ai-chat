"""上下文子系统 DI 容器。"""

from typing import Any

from dependency_injector import containers, providers


def _create_system_collector():
    """系统环境收集器。"""
    from src.ai.core.context.collectors.system_collector import SystemCollector

    return SystemCollector()


def _create_user_collector(prompt_service):
    """用户系统提示收集器。"""
    from src.ai.core.context.collectors.user_collector import UserCollector

    return UserCollector(prompt_service=prompt_service)


def _create_memory_collector(memory_service):
    """记忆上下文收集器。"""
    from src.ai.core.context.collectors.memory_collector import MemoryCollector

    return MemoryCollector(memory_service=memory_service)


def _create_tool_collector(tool_registry):
    """工具描述收集器。"""
    from src.ai.core.context.collectors.tool_collector import ToolCollector

    return ToolCollector(tool_registry=tool_registry)


def _create_mcp_collector(mcp_manager):
    """MCP 状态收集器。"""
    from src.ai.core.context.collectors.mcp_collector import MCPCollector

    return MCPCollector(mcp_manager=mcp_manager)


def _create_skill_collector(skill_service):
    """技能元数据收集器。"""
    from src.ai.core.context.collectors.skill_collector import SkillCollector

    return SkillCollector(skill_service=skill_service)


def _create_rag_collector(rag_encoder, settings):
    """RAG 检索收集器。"""
    from src.ai.core.context.collectors.rag_collector import RAGCollector

    return RAGCollector(rag_encoder=rag_encoder, settings=settings)


def _create_coordinator(collectors):
    """并行收集协调器。"""
    from src.ai.core.context.collector import ContextCoordinator

    return ContextCoordinator(collectors=list(collectors))


def _create_sections():
    """段缓存管理器。"""
    from src.ai.core.context.sections import SystemPromptSections

    return SystemPromptSections()


def _create_assembler(settings):
    """token 预算组装器。"""
    from src.ai.core.context.assembler import ContextAssembler

    return ContextAssembler(settings=settings)


def _create_micro_compact(settings):
    """微压缩器。"""
    from src.ai.core.context.compact import MicroCompact

    max_chars = settings.memory.micro_compact_max_tool_chars
    return MicroCompact(max_tool_result_chars=max_chars)


def _create_context_restorer():
    """压缩后上下文恢复器。"""
    from src.ai.core.context.restore import ContextRestorer

    return ContextRestorer()


def _create_chat_history_manager(settings, file_store):
    """创建 ChatHistoryManager。"""
    from src.ai.core.memory.history import ChatHistoryManager
    from src.ai.storage.database import get_engine

    return ChatHistoryManager(
        file_store=file_store,
        table_name=settings.memory.history_table_name,
        engine=get_engine(),
        history_file_enabled=settings.memory.history_file_enabled,
    )


def _create_memory_strategy(history_manager, file_store, llm, prompt_service, settings):
    """创建 CompressionStrategy。"""
    from src.ai.core.context.strategies import create_memory_strategy

    return create_memory_strategy(
        history_manager,
        file_store,
        llm,
        prompt_service,
        max_messages=settings.memory.compression_max_messages,
        keep_recent=settings.memory.compression_keep_recent,
        full_compact_threshold=settings.memory.full_compact_threshold,
    )


def _create_context_service(
    coordinator,
    assembler,
    sections,
    strategy,
    micro_compact,
    restorer,
):
    """上下文服务。"""
    from src.ai.core.context.service import ContextService

    return ContextService(
        coordinator=coordinator,
        assembler=assembler,
        sections=sections,
        strategy=strategy,
        micro_compact=micro_compact,
        restorer=restorer,
    )


def _create_rag_encoder(settings, llm, rag_service):
    """RAG 查询优化器。"""
    if not settings.rag.rag_optimize_query:
        return None

    try:
        from src.ai.core.rag.encoder import RAGQueryEncoder

        return RAGQueryEncoder(llm=llm, rag_service=rag_service)
    except Exception:
        import logging

        logging.getLogger(__name__).warning("RAG 编码器初始化失败", exc_info=True)
        return None


class ContextContainer(containers.DeclarativeContainer):
    """上下文子系统容器。"""

    # 外部依赖
    settings: Any = providers.Dependency()
    memory_service: Any = providers.Dependency()
    tool_registry: Any = providers.Dependency()
    prompt_service: Any = providers.Dependency()
    llm: Any = providers.Dependency()
    rag_service: Any = providers.Dependency()
    file_store: Any = providers.Dependency()
    mcp_manager: Any = providers.Dependency()
    skill_service: Any = providers.Dependency()

    # 内部组件：系统收集器
    system_collector = providers.Singleton(_create_system_collector)
    user_collector = providers.Singleton(
        _create_user_collector,
        prompt_service=prompt_service,
    )
    memory_collector = providers.Singleton(
        _create_memory_collector,
        memory_service=memory_service,
    )
    tool_collector = providers.Singleton(
        _create_tool_collector,
        tool_registry=tool_registry,
    )
    mcp_collector = providers.Singleton(
        _create_mcp_collector,
        mcp_manager=mcp_manager,
    )
    skill_collector = providers.Singleton(
        _create_skill_collector,
        skill_service=skill_service,
    )
    rag_encoder = providers.Singleton(
        _create_rag_encoder,
        settings=settings,
        llm=llm,
        rag_service=rag_service,
    )
    rag_collector = providers.Singleton(
        _create_rag_collector,
        rag_encoder=rag_encoder,
        settings=settings,
    )

    coordinator = providers.Singleton(
        _create_coordinator,
        collectors=providers.List(
            system_collector,
            user_collector,
            memory_collector,
            tool_collector,
            mcp_collector,
            skill_collector,
            rag_collector,
        ),
    )
    sections = providers.Singleton(_create_sections)
    assembler = providers.Singleton(_create_assembler, settings=settings)
    micro_compact = providers.Singleton(
        _create_micro_compact,
        settings=settings,
    )
    context_restorer = providers.Singleton(_create_context_restorer)

    # 内部组件：记忆策略（从 memory 模块迁入）
    chat_history_manager = providers.Singleton(
        _create_chat_history_manager,
        settings=settings,
        file_store=file_store,
    )
    memory_strategy = providers.Singleton(
        _create_memory_strategy,
        history_manager=chat_history_manager,
        file_store=file_store,
        llm=llm,
        prompt_service=prompt_service,
        settings=settings,
    )

    # 最终服务
    context_service = providers.Singleton(
        _create_context_service,
        coordinator=coordinator,
        assembler=assembler,
        sections=sections,
        strategy=memory_strategy,
        micro_compact=micro_compact,
        restorer=context_restorer,
    )
