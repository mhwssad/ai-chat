"""容器启动 — 初始化 DI 容器并执行后置组装。"""

import asyncio
import threading

from src.ai.config.logging_setup import get_logger
from src.ai.core.container import container

logger = get_logger(__name__)

_initialized = False


async def initialize_container() -> None:
    """初始化 DI 容器并执行所有后置组装。

    幂等操作：首次调用时依次执行建表、种子数据、技能发现、工具注册、
    调度器启动；后续调用直接返回。
    """
    global _initialized
    if _initialized:
        return

    # 0. Wired 路由模块（启用 @inject + Provide 注入）
    container.wire(
        modules=[
            "src.ai.api.routes.chat",
            "src.ai.api.routes.tools",
            "src.ai.api.routes.system",
            "src.ai.api.routes.rag",
            "src.ai.api.routes.agent",
            "src.ai.api.routes.prompts",
            "src.ai.api.routes.memory",
            "src.ai.api.routes.models",
            "src.ai.api.routes.sessions",
            "src.ai.api.routes.image",
            "src.ai.api.routes.tts",
            "src.ai.api.routes.scheduler",
            "src.ai.api.routes.skills",
        ],
    )

    # 1. 确保数据库表已创建
    from src.ai.storage.database import init_database

    init_database()

    # 2. 种子提示词模板
    from src.ai.core.prompts.seeder import seed_default_prompts

    store = container.storage_container.db_prompt_store()
    seed_default_prompts(store)

    # 技能发现 — 仅扫描 frontmatter 建立内存索引
    _initialize_skills()

    # 注册有依赖的工具（包括定时任务工具），等待 MCP 工具发现完成
    await _register_dependent_tools()

    # 启动定时任务调度器
    _start_scheduler()

    logger.info("DI 容器初始化完成")
    _initialized = True


def _initialize_skills() -> None:
    """技能发现 — 仅扫描 frontmatter 建立内存索引。"""
    skill_svc = container.skill_container.skill_service()
    skill_svc.discover()
    logger.info("技能索引构建完成")


def shutdown_container() -> None:
    """关闭容器，释放资源。在 app 关闭时调用。"""
    global _initialized
    if not _initialized:
        return

    # 停止定时任务调度器
    _stop_scheduler()

    # 释放数据库引擎和连接池
    from src.ai.storage.database import close_database

    close_database()

    _initialized = False


async def _register_dependent_tools() -> None:
    """注册所有工具和插件，等待 MCP 工具发现完成。"""
    mgr = container.tool_container.tool_manager()

    # 1. 注册插件（必须在 load_builtin_tools 之前）
    mcp_mgr = container.mcp_container.mcp_manager()
    mgr.register_plugin(mcp_mgr)

    # 2. 获取可选的调度器服务
    scheduler_service = None
    try:
        scheduler_service = container.scheduler_container.scheduler_service()
    except Exception as e:
        logger.debug("定时任务服务未初始化，跳过注册调度器工具: %s", str(e))

    # 3. 加载内置工具 + 执行插件注册 + 注册有依赖的工具
    #    load_builtin_tools 内部会设置活跃注册表、导入 builtins 模块、
    #    调用 register_dependent_tools 并执行所有插件的 register_tools
    mgr.load_builtin_tools(scheduler_service=scheduler_service, mcp_manager=mcp_mgr)

    # 4. 等待 MCP 工具同步完成（超时 30s）
    await mcp_mgr.await_sync(timeout=30.0)


def _start_scheduler() -> None:
    """启动定时任务调度器。

    在异步上下文（FastAPI）中使用 ensure_future；在同步上下文
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
            # 同步上下文，后台守护线程启动调度器
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
