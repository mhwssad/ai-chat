"""自动发现并注册 providers 目录下的存储后端实现。

模块加载时扫描同目录下所有 Python 模块，导入后查找 MemoryProvider 的
具体子类，收集到 exported 字典中并注入到包命名空间。
触发 @register_memory 装饰器完成自动注册。
"""

import importlib
import pkgutil
from pathlib import Path

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.memory.models import MemoryProvider

logger = get_logger(__name__)

package_dir = Path(__file__).parent
exported: dict[str, type] = {}

for info in pkgutil.iter_modules([str(package_dir)]):
    mod = importlib.import_module(f"{__name__}.{info.name}")
    for attr in dir(mod):
        obj = getattr(mod, attr)
        if isinstance(obj, type) and issubclass(obj, MemoryProvider) and obj is not MemoryProvider:
            exported[attr] = obj
            logger.debug("发现存储后端: %s (来自 %s)", attr, info.name)

logger.info("自动发现完成，共 %d 个存储后端: %s", len(exported), list(exported.keys()))
globals().update(exported)
__all__ = list(exported)
