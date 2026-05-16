"""递归自动发现并注册 providers 目录下所有供应商策略。"""

import importlib
import pkgutil
from pathlib import Path

from src.ai_chat.llm.base import ModelProvider


def _auto_discover() -> dict:
    """递归扫描 providers 目录及子目录，导入所有模块以触发注册装饰器。"""
    package_dir = Path(__file__).parent
    exported: dict[str, type] = {}
    prefix = __name__

    for importer, modname, ispkg in pkgutil.walk_packages(
        path=[str(package_dir)], prefix=f"{prefix}."
    ):
        # 跳过包自身的 __init__，只导入叶子模块
        if ispkg:
            continue
        mod = importlib.import_module(modname)
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if (
                isinstance(obj, type)
                and issubclass(obj, ModelProvider)
                and obj is not ModelProvider
                and not getattr(obj, "__abstractmethods__", None)
            ):
                exported[attr] = obj
    return exported


_providers = _auto_discover()
globals().update(_providers)
__all__ = list(_providers)
