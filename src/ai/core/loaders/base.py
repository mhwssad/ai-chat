"""文档加载器基类和接口定义。

包含：
- DocumentLoader: 文档加载器抽象基类
- DocumentMetadata/LoadedDocument: 数据类
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DocumentMetadata:
    """文档元数据。"""

    source_path: str
    title: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    file_label: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LoadedDocument:
    """已加载的文档对象。"""

    content: str
    metadata: DocumentMetadata


class DocumentLoader(ABC):
    """文档加载器抽象基类。"""

    @abstractmethod
    def load(self, path: str | Path) -> LoadedDocument:
        """加载指定路径的文档。

        Args:
            path: 文件路径。

        Returns:
            LoadedDocument: 已加载的文档对象。

        Raises:
            LoaderError: 加载失败时抛出。
        """

    def load_multiple(self, paths: list[str | Path]) -> list[LoadedDocument]:
        """批量加载多个文档。

        Args:
            paths: 文件路径列表。

        Returns:
            list[LoadedDocument]: 已加载的文档列表。
        """
        return [self.load(path) for path in paths]
