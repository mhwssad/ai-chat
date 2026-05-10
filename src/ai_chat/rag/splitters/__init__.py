"""自动发现并注册文本分割器。"""

import importlib
import pkgutil
from pathlib import Path

from ..models import TextSplitter

package_dir = Path(__file__).parent
exported: dict[str, type] = {}
for info in pkgutil.iter_modules([str(package_dir)]):
    mod = importlib.import_module(f"{__name__}.{info.name}")
    for attr in dir(mod):
        obj = getattr(mod, attr)
        if isinstance(obj, type) and issubclass(obj, TextSplitter) and obj is not TextSplitter:
            exported[attr] = obj

globals().update(exported)
__all__ = list(exported)
