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
    """注册所有工具和插件。"""
    from src.ai.core.tools.builtins import register_dependent_tools

    registry = container.tool_container.tool_registry()
    mgr = container.tool_container.tool_manager()

    # 1. 注册插件（必须在 load_builtin_tools 之前）
    mcp_mgr = container.mcp_container.mcp_manager()
    mgr.register_plugin(mcp_mgr)

    skill_svc = container.skill_container.skill_service()
    mgr.register_plugin(skill_svc)

    # 2. 加载内置工具 + 执行插件注册
    mgr.load_builtin_tools()

    # 3. 注册有依赖的内置工具
    scheduler_service = None
    try:
        scheduler_service = container.scheduler_container.scheduler_service()
    except Exception as e:
        logger.debug("定时任务服务未初始化，跳过注册调度器工具: %s", str(e))

    register_dependent_tools(
        http_aclient=container.http_container.http_aclient(),
        registry=registry,
        scheduler_service=scheduler_service,
    )


def _start_scheduler() -> None:
    """启动定时任务调度器。"""
    try:
        scheduler_svc = container.scheduler_container.scheduler_service()
        # 在事件循环中启动调度器
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            asyncio.ensure_future(scheduler_svc.start())
        else:
            asyncio.run(scheduler_svc.start())
        logger.info("定时任务调度器已启动")
    except Exception as e:
        logger.warning("定时任务调度器启动失败: %s", str(e))


def _stop_scheduler() -> None:
    """停止定时任务调度器。"""
    try:
        scheduler_svc = container.scheduler_container.scheduler_service()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            asyncio.ensure_future(scheduler_svc.stop())
        else:
            asyncio.run(scheduler_svc.stop())
        logger.info("定时任务调度器已停止")
    except Exception as e:
        logger.debug("停止调度器时出错: %s", str(e))
