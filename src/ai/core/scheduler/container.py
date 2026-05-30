"""定时任务调度器 DI 容器。"""

from __future__ import annotations

from typing import Any

from dependency_injector import containers, providers


def _create_scheduler_store(session_factory: Any) -> Any:
    """创建 SchedulerStore。"""
    from src.ai.core.scheduler.store import SchedulerStore

    return SchedulerStore(session_factory=session_factory)


def _create_scheduler_manager(
    settings: Any,
    store: Any,
    tool_manager: Any,
    llm: Any,
) -> Any:
    """创建 SchedulerManager。"""
    from src.ai.core.scheduler.manager import SchedulerManager

    return SchedulerManager(
        settings=settings.scheduler,
        store=store,
        tool_manager=tool_manager,
        llm=llm,
    )


def _create_scheduler_service(
    manager: Any,
    store: Any,
    settings: Any,
) -> Any:
    """创建 SchedulerService。"""
    from src.ai.core.scheduler.service import SchedulerService

    service = SchedulerService(
        manager=manager,
        store=store,
        settings=settings.scheduler,
    )

    # 设置回调，让 manager 在任务执行后通知 service 更新统计
    manager.set_task_executed_callback(service.update_task_after_execution)

    return service


class SchedulerContainer(containers.DeclarativeContainer):
    """定时任务调度器子系统容器。"""

    settings = providers.Dependency()
    session_factory = providers.Dependency()
    tool_manager = providers.Dependency()
    llm = providers.Dependency()

    # Layer 1: 存储层
    scheduler_store = providers.Singleton(
        _create_scheduler_store,
        session_factory=session_factory,
    )

    # Layer 2: 管理器
    scheduler_manager = providers.Singleton(
        _create_scheduler_manager,
        settings=settings,
        store=scheduler_store,
        tool_manager=tool_manager,
        llm=llm,
    )

    # Layer 3: 服务门面
    scheduler_service = providers.Singleton(
        _create_scheduler_service,
        manager=scheduler_manager,
        store=scheduler_store,
        settings=settings,
    )
