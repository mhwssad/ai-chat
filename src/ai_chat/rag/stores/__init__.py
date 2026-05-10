"""自动发现并注册向量存储后端。"""

import importlib
import pkgutil
from pathlib import Path

from ..models import VectorStoreProvider

package_dir = Path(__file__).parent
exported: dict[str, type] = {}
for info in pkgutil.iter_modules([str(package_dir)]):
    mod = importlib.import_module(f"{__name__}.{info.name}")
    for attr in dir(mod):
        obj = getattr(mod, attr)
        if isinstance(obj, type) and issubclass(obj, VectorStoreProvider) and obj is not VectorStoreProvider:
            exported[attr] = obj

globals().update(exported)
__all__ = list(exported)
