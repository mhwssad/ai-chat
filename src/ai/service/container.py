"""共享服务层 DI 容器。

遵循项目子容器模式（参考 core/tools/container.py、core/memory/container.py），
所有类导入延迟到工厂函数内部，避免 import 时触发 langchain_core 冷启动。
"""

from __future__ import annotations

from typing import Any

from dependency_injector import containers, providers


def _create_chat_service(
    *,
    model_service: Any,
    context_service: Any,
    tool_manager: Any,
    memory_service: Any,
    chat_history_manager: Any,
    chat_llm: Any,
    thread_pool: Any,
) -> Any:
    """创建统一 ChatService。"""
    from src.ai.service.chat_service import ChatService

    return ChatService(
        model_service=model_service,
        context_service=context_service,
        tool_manager=tool_manager,
        memory_service=memory_service,
        chat_history_manager=chat_history_manager,
        chat_llm=chat_llm,
        thread_pool=thread_pool,
    )


def _create_image_service(
    *,
    model_service: Any,
    thread_pool: Any,
) -> Any:
    """创建统一 ImageService。"""
    from src.ai.service.image_service import ImageService

    return ImageService(
        model_service=model_service,
        thread_pool=thread_pool,
    )


def _create_tts_service(
    *,
    model_service: Any,
    thread_pool: Any,
) -> Any:
    """创建统一 TTSService。"""
    from src.ai.service.tts_service import TTSService

    return TTSService(
        model_service=model_service,
        thread_pool=thread_pool,
    )


def _create_tool_service(
    *,
    tool_registry: Any,
    tool_manager: Any,
) -> Any:
    """创建统一 ToolService。"""
    from src.ai.service.tool_service import ToolService

    return ToolService(
        tool_registry=tool_registry,
        tool_manager=tool_manager,
    )


def _create_system_service(
    *,
    model_service: Any,
    scheduler_service: Any,
    memory_service: Any,
    tool_service: Any,
    settings: Any,
    thread_pool: Any,
) -> Any:
    """创建统一 SystemService。"""
    from src.ai.service.system_service import SystemService

    return SystemService(
        model_service=model_service,
        scheduler_service=scheduler_service,
        memory_service=memory_service,
        tool_service=tool_service,
        settings=settings,
        thread_pool=thread_pool,
    )


class ServiceContainer(containers.DeclarativeContainer):
    """共享服务层容器。

    Layer 4 服务，依赖 Layer 2 子容器提供的核心组件。
    """

    # 外部依赖（由 AppContainer 注入）
    model_service: Any = providers.Dependency()
    context_service: Any = providers.Dependency()
    tool_manager: Any = providers.Dependency()
    tool_registry: Any = providers.Dependency()
    memory_service: Any = providers.Dependency()
    chat_history_manager: Any = providers.Dependency()
    chat_llm: Any = providers.Dependency()
    thread_pool: Any = providers.Dependency()
    scheduler_service: Any = providers.Dependency()
    settings: Any = providers.Dependency()

    # 共享服务
    chat_service = providers.Singleton(
        _create_chat_service,
        model_service=model_service,
        context_service=context_service,
        tool_manager=tool_manager,
        memory_service=memory_service,
        chat_history_manager=chat_history_manager,
        chat_llm=chat_llm,
        thread_pool=thread_pool,
    )
    image_service = providers.Singleton(
        _create_image_service,
        model_service=model_service,
        thread_pool=thread_pool,
    )
    tts_service = providers.Singleton(
        _create_tts_service,
        model_service=model_service,
        thread_pool=thread_pool,
    )
    tool_service = providers.Singleton(
        _create_tool_service,
        tool_registry=tool_registry,
        tool_manager=tool_manager,
    )
    system_service = providers.Singleton(
        _create_system_service,
        model_service=model_service,
        scheduler_service=scheduler_service,
        memory_service=memory_service,
        tool_service=tool_service,
        settings=settings,
        thread_pool=thread_pool,
    )
