"""启动注入 — 委托给 DI 容器初始化。

在 app 启动时调用 wire_core_with_db()，将 storage 层的具体实现
注入到 core 层的 Protocol/Callback 依赖中。
"""

import logging

logger = logging.getLogger(__name__)

_wired = False


def wire_core_with_db() -> None:
    """将 DB 实现注入 core 层单例。

    在 init_database() 之后调用。可安全重复调用（幂等）。
    委托给 DI 容器的 initialize_container()。
    """
    global _wired
    if _wired:
        return

    from src.ai.core.container_wiring import initialize_container

    initialize_container()

    logger.info("core 层 DB 注入完成")
    _wired = True


def get_default_callbacks() -> list:
    """获取默认 callbacks 列表（含审计）。"""
    from src.ai.core.callbacks.audit import AuditCallbackHandler

    return [AuditCallbackHandler()]
