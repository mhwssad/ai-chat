"""记忆子系统 DI 容器。

所有子模块导入延迟到工厂函数内部，避免 import 时触发 langchain_core 冷启动。
"""

from __future__ import annotations

from typing import Any

from dependency_injector import containers, providers


def _create_file_store(settings: Any) -> Any:
    """创建 FileHistoryStore。"""
    from src.ai.config.base_config import project_root
    from src.ai.core.memory.history_store import FileHistoryStore

    return FileHistoryStore(project_root / settings.memory.memory_dir)


def _create_memory_store(settings: Any) -> Any:
    """创建 MemoryStore。"""
    from src.ai.config.base_config import project_root
    from src.ai.core.memory.paths import MemoryPathResolver
    from src.ai.core.memory.store import MemoryStore

    memory_base = project_root / settings.memory.memory_dir
    resolver = MemoryPathResolver(memory_base=memory_base)
    return MemoryStore(resolver.auto_memory_dir())


def _create_memory_extractor(llm: Any, prompt_service: Any) -> Any:
    """创建 MemoryExtractor。"""
    from src.ai.core.memory.extractor import MemoryExtractor

    return MemoryExtractor(llm=llm, prompt_service=prompt_service)


def _create_prompt_builder(prompt_service: Any) -> Any:
    """创建 MemoryPromptBuilder。"""
    from src.ai.core.memory.prompt import MemoryPromptBuilder

    return MemoryPromptBuilder(prompt_service=prompt_service)


def _create_memory_vector_store(settings: Any) -> Any:
    """创建 MemoryVectorStore。"""
    from src.ai.config.base_config import project_root
    from src.ai.core.memory.vector_store import MemoryVectorStore

    memory_dir = project_root / settings.memory.memory_dir
    return MemoryVectorStore(
        persist_directory=str(memory_dir / "vectors"),
        collection_name="memory_vectors",
    )


def _create_memory_searcher(
    store: Any, llm: Any, prompt_service: Any, settings: Any, vector_store: Any = None
) -> Any:
    """创建 MemorySearcher。"""
    from src.ai.core.memory.searcher import MemorySearcher

    return MemorySearcher(
        store=store,
        llm=llm,
        prompt_service=prompt_service,
        max_results=settings.memory.relevance_max_results,
        vector_store=vector_store,
    )


def _create_memory_service(
    store: Any,
    extractor: Any,
    prompt_builder: Any,
    searcher: Any,
    vector_store: Any = None,
) -> Any:
    """创建 MemoryService。"""
    from src.ai.core.memory.service import MemoryService

    return MemoryService(
        store=store,
        extractor=extractor,
        prompt_builder=prompt_builder,
        searcher=searcher,
        vector_store=vector_store,
    )


class MemoryContainer(containers.DeclarativeContainer):
    """记忆子系统容器。"""

    settings = providers.Dependency()
    llm = providers.Dependency()
    prompt_service = providers.Dependency()

    # Layer 1: 基础依赖
    file_store = providers.Singleton(_create_file_store, settings=settings)
    memory_store = providers.Singleton(_create_memory_store, settings=settings)
    vector_store = providers.Singleton(_create_memory_vector_store, settings=settings)

    # Layer 2: 依赖 Layer 1
    memory_extractor = providers.Singleton(
        _create_memory_extractor, llm=llm, prompt_service=prompt_service
    )
    prompt_builder = providers.Singleton(
        _create_prompt_builder, prompt_service=prompt_service
    )
    memory_searcher = providers.Singleton(
        _create_memory_searcher,
        store=memory_store,
        llm=llm,
        prompt_service=prompt_service,
        settings=settings,
        vector_store=vector_store,
    )

    # Layer 3: 顶层服务
    memory_service = providers.Singleton(
        _create_memory_service,
        store=memory_store,
        extractor=memory_extractor,
        prompt_builder=prompt_builder,
        searcher=memory_searcher,
        vector_store=vector_store,
    )
