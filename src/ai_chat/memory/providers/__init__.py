"""自动发现并注册存储后端。"""

import importlib
import pkgutil
from pathlib import Path

from src.ai_chat.memory.models import MemoryProvider

package_dir = Path(__file__).parent
exported: dict[str, type] = {}

for info in pkgutil.iter_modules([str(package_dir)]):
    mod = importlib.import_module(f"{__name__}.{info.name}")
    for attr in dir(mod):
        obj = getattr(mod, attr)
        if isinstance(obj, type) and issubclass(obj, MemoryProvider) and obj is not MemoryProvider:
            exported[attr] = obj

globals().update(exported)
__all__ = list(exported)
