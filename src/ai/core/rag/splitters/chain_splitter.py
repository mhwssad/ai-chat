"""职责链切割器编排器。"""

import logging
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from .base import SplitChunk, SplitterStrategy
from .registry import SplitterRegistry

logger = logging.getLogger(__name__)


class ChainSplitter(SplitterStrategy):
    """职责链编排器。

    遍历注册表中的切割器，按优先级依次尝试。
    首个成功产出结果的切割器胜出。

    Args:
        registry: 切割器注册表，None 时使用全局单例。
        **kwargs: 传递给各切割器构造函数的额外参数。
    """

    def __init__(
        self,
        registry: SplitterRegistry | None = None,
        **kwargs: Any,
    ) -> None:
        if registry is not None:
            self._registry = registry
        else:
            from . import splitter_registry  # 惰性导入，避免循环依赖

            self._registry = splitter_registry
        self._kwargs = kwargs

    def can_file_handle(self, file_path: Path) -> bool:
        """编排器始终可以尝试。"""
        return True

    def can_text_handle(self, text: str, metadata: dict[str, Any]) -> bool:
        """编排器始终可以尝试。"""
        return True

    def split_text(
        self, text: str, *, metadata: dict[str, Any] | None = None
    ) -> list[SplitChunk]:
        """按优先级遍历切割器链，首个成功的返回结果。"""
        meta = metadata or {}
        for entry in self._registry.get_entries():
            splitter = entry.splitter_cls(**self._kwargs)
            if not splitter.can_text_handle(text, meta):
                continue
            try:
                chunks = splitter.split_text(text, metadata=meta)
                if chunks:
                    logger.debug(
                        "切割器 %s 成功切割 %d 个片段", entry.name, len(chunks)
                    )
                    return chunks
            except Exception as e:
                logger.debug(
                    "切割器 %s 失败 (%s: %s)，尝试下一个",
                    entry.name,
                    type(e).__name__,
                    e,
                )
                continue

        # 兜底：RecursiveSplitter 应该始终能处理
        return []

    def split_document(self, doc: Document) -> list[SplitChunk]:
        """按优先级遍历切割器链，结合文件路径和内容判断。"""
        source = doc.metadata.get("source", "")
        file_path = Path(source) if source else None

        for entry in self._registry.get_entries():
            splitter = entry.splitter_cls(**self._kwargs)
            if file_path and not splitter.can_file_handle(file_path):
                continue
            if not splitter.can_text_handle(doc.page_content, doc.metadata):
                continue
            try:
                chunks = splitter.split_document(doc)
                if chunks:
                    logger.debug(
                        "切割器 %s 成功切割 %d 个片段", entry.name, len(chunks)
                    )
                    return chunks
            except Exception as e:
                logger.debug(
                    "切割器 %s 失败 (%s: %s)，尝试下一个",
                    entry.name,
                    type(e).__name__,
                    e,
                )
                continue

        return []
