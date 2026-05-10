"""自动发现并注册文档加载器。"""

import importlib
import pkgutil
from pathlib import Path

from ..models import DocumentLoader

package_dir = Path(__file__).parent
exported: dict[str, type] = {}
for info in pkgutil.iter_modules([str(package_dir)]):
    mod = importlib.import_module(f"{__name__}.{info.name}")
    for attr in dir(mod):
        obj = getattr(mod, attr)
        if isinstance(obj, type) and issubclass(obj, DocumentLoader) and obj is not DocumentLoader:
            exported[attr] = obj

globals().update(exported)
__all__ = list(exported)
