"""容器启动 — 初始化 DI 容器并执行后置组装。"""

import asyncio
import logging
import threading

from src.ai.core.container import container

logger = logging.getLogger(__name__)

_initialized = False


def initialize_container() -> None:
    """初始化 DI 容器并执行所有后置组装。

    幂等操作：首次调用时依次执行建表、种子数据、技能发现、工具注册、
    调度器启动；后续调用直接返回。
    """
    global _initialized
    if _initialized:
        return

    # 1. 确保数据库表已创建
    from src.ai.storage.database import init_database

    init_database()

    # 2. 种子提示词模板
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
    mgr = container.tool_container.tool_manager()

    # 1. 注册插件（必须在 load_builtin_tools 之前）
    mcp_mgr = container.mcp_container.mcp_manager()
    mgr.register_plugin(mcp_mgr)

    skill_svc = container.skill_container.skill_service()
    mgr.register_plugin(skill_svc)

    # 2. 获取可选的调度器服务
    scheduler_service = None
    try:
        scheduler_service = container.scheduler_container.scheduler_service()
    except Exception as e:
        logger.debug("定时任务服务未初始化，跳过注册调度器工具: %s", str(e))

    # 3. 加载内置工具 + 执行插件注册 + 注册有依赖的工具
    #    load_builtin_tools 内部会设置活跃注册表、导入 builtins 模块、
    #    调用 register_dependent_tools 并执行所有插件的 register_tools
    mgr.load_builtin_tools(scheduler_service=scheduler_service)


def _start_scheduler() -> None:
    """启动定时任务调度器。

    在异步上下文（FastAPI）中使用 ensure_future；在同步上下文（CLI）
    中以后台守护线程运行，避免阻塞主线程。
    """
    try:
        scheduler_svc = container.scheduler_container.scheduler_service()

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 已有运行中的事件循环（FastAPI lifespan 等）
            asyncio.ensure_future(scheduler_svc.start())
        else:
            # 同步上下文（CLI），后台守护线程启动调度器
            def _run() -> None:
                try:
                    asyncio.run(scheduler_svc.start())
                except Exception:
                    logger.debug("调度器后台线程异常退出", exc_info=True)

            t = threading.Thread(target=_run, daemon=True, name="scheduler")
            t.start()
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
