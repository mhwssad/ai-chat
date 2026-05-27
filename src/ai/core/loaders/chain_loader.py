"""职责链加载器编排器。"""

import logging
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from src.ai.exception.loader_exception import LoaderError
from .base import LoaderStrategy
from .registry import LoaderRegistry, loader_registry

logger = logging.getLogger(__name__)


class ChainLoader(LoaderStrategy):
    """职责链编排器。

    遍历注册表中的加载器，按优先级依次尝试。
    首个成功产出文档的加载器胜出，后续加载器不再执行。
    不硬编码任何具体加载器，新增策略只需注册即可。

    Args:
        registry: 加载器注册表，None 时使用全局单例。
        **kwargs: 传递给各加载器构造函数的额外参数。
    """

    def __init__(
        self,
        registry: LoaderRegistry | None = None,
        **kwargs: Any,
    ) -> None:
        self._registry = registry or loader_registry
        self._kwargs = kwargs

    def can_handle(self, file_path: Path) -> bool:
        """编排器始终可以尝试。"""
        return True

    def _load_single(self, file_path: Path) -> list[Document]:
        """按优先级遍历加载器链，首个成功的返回结果。"""
        for entry in self._registry.get_entries():
            loader = entry.loader_cls(**self._kwargs)
            if not loader.can_handle(file_path):
                continue
            try:
                docs = loader._load_single(file_path)
                if docs:
                    logger.debug(
                        "加载器 %s 成功加载 %d 个文档", entry.name, len(docs)
                    )
                    return docs
            except LoaderError:
                raise
            except Exception as e:
                logger.debug(
                    "加载器 %s 失败 (%s: %s)，尝试下一个",
                    entry.name,
                    type(e).__name__,
                    e,
                )
                continue

        raise LoaderError(
            f"所有加载策略均失败: {file_path}",
            path=str(file_path),
        )
