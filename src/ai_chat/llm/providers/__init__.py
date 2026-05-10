"""自动发现并注册 providers 目录下所有供应商策略。"""

import importlib
import pkgutil
from pathlib import Path

from ..models import ChatProvider, EmbeddingProvider


def _auto_discover() -> dict:
    """扫描 providers 目录，导入所有模块以触发 @register_chat / @register_embedding 装饰器。"""
    package_dir = Path(__file__).parent
    exported: dict[str, type] = {}
    for info in pkgutil.iter_modules([str(package_dir)]):
        mod = importlib.import_module(f"{__name__}.{info.name}")
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if isinstance(obj, type) and (
                issubclass(obj, ChatProvider) or issubclass(obj, EmbeddingProvider)
            ):
                exported[attr] = obj
    return exported


_providers = _auto_discover()
globals().update(_providers)
__all__ = list(_providers)
