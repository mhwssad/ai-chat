"""递归自动发现并注册 providers 目录下所有供应商策略。

模块加载时自动扫描 providers 目录及其子目录（chat/、embedding/、image/、video/），
导入所有叶子模块以触发 @register_chat / @register_embedding 装饰器，
完成供应商的自动注册到全局 llm_factory。
"""

import importlib
import pkgutil
from pathlib import Path

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.base import ModelProvider

logger = get_logger(__name__)


def _auto_discover() -> dict:
    """递归扫描 providers 目录及子目录，导入所有模块以触发注册装饰器。

    扫描规则：
    - 跳过包自身的 __init__.py（只导入叶子模块）
    - 过滤出 ModelProvider 的非抽象子类
    - 返回 {类名: 类对象} 的映射字典

    Returns:
        发现到的所有具体 Provider 类的映射字典
    """
    package_dir = Path(__file__).parent
    exported: dict[str, type] = {}
    prefix = __name__

    logger.info("开始自动发现 providers，扫描目录: %s", package_dir)

    for importer, modname, ispkg in pkgutil.walk_packages(
        path=[str(package_dir)], prefix=f"{prefix}."
    ):
        # 跳过包自身的 __init__，只导入叶子模块
        if ispkg:
            continue
        logger.debug("导入模块: %s", modname)
        mod = importlib.import_module(modname)
        # 从模块中提取 ModelProvider 的具体子类
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if (
                isinstance(obj, type)
                and issubclass(obj, ModelProvider)
                and obj is not ModelProvider
                and not getattr(obj, "__abstractmethods__", None)
            ):
                exported[attr] = obj
                logger.debug("发现 Provider 类: %s (来自 %s)", attr, modname)

    logger.info("自动发现完成，共发现 %d 个 Provider 类: %s", len(exported), list(exported.keys()))
    return exported


_providers = _auto_discover()
globals().update(_providers)
__all__ = list(_providers)
