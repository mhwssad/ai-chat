"""容器启动 — 初始化 DI 容器并执行后置组装。"""

import asyncio
import logging

from src.ai.core.container import container

logger = logging.getLogger(__name__)

_initialized = False


def initialize_container() -> None:
    """初始化 DI 容器并执行所有后置组装。在 init_database() 之后调用。"""
    global _initialized
    if _initialized:
        return

    # 种子提示词模板
    from src.ai.core.prompts.seeder import seed_default_prompts

    store = container.storage_container.db_prompt_store()
    seed_default_prompts(store)

    # 技能发现
    skill_svc = container.skill_container.skill_service()
    skill_svc.discover()

    # 注册有依赖的工具（包括定时任务工具）
    _register_dependent_tools()

    # 启动定时任务调度器
    _start_scheduler()

    logger.info("DI 容器初始化完成")
    _initialized = True


def shutdown_container() -> None:
    """关闭容器，释放资源。在 app 关闭时调用。"""
    global _initialized
    if not _initialized:
        return

    # 停止定时任务调度器
    _stop_scheduler()

    _initialized = False


def _register_dependent_tools() -> None:
    """注册有依赖的工具（内置 + Skills）。"""
    from src.ai.core.tools.builtins import register_dependent_tools

    registry = container.tool_container.tool_registry()

    # 获取定时任务服务（可选）
    scheduler_service = None
    try:
        scheduler_service = container.scheduler_container.scheduler_service()
    except Exception as e:
        logger.debug("定时任务服务未初始化，跳过注册调度器工具: %s", str(e))

    # 内置工具（web_tools、search_tools、scheduler_tools）
    register_dependent_tools(
        http_aclient=container.http_container.http_aclient(),
        mcp_manager=container.mcp_container.mcp_manager(),
        registry=registry,
        scheduler_service=scheduler_service,
    )

    # Skills 模块自行注册技能工具
    skill_svc = container.skill_container.skill_service()
    skill_svc.register_tools(registry)


def _start_scheduler() -> None:
    """启动定时任务调度器。"""
    try:
        scheduler_svc = container.scheduler_container.scheduler_service()
        # 在事件循环中启动调度器
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(scheduler_svc.start())
        else:
            loop.run_until_complete(scheduler_svc.start())
        logger.info("定时任务调度器已启动")
    except Exception as e:
        logger.warning("定时任务调度器启动失败: %s", str(e))


def _stop_scheduler() -> None:
    """停止定时任务调度器。"""
    try:
        scheduler_svc = container.scheduler_container.scheduler_service()
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(scheduler_svc.stop())
        else:
            loop.run_until_complete(scheduler_svc.stop())
        logger.info("定时任务调度器已停止")
    except Exception as e:
        logger.debug("停止调度器时出错: %s", str(e))
