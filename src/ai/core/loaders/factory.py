"""统一的文档加载工厂，使用 UnifiedLoader 处理所有文件类型。"""

from __future__ import annotations

from pathlib import Path

from .base import DocumentLoader, LoadedDocument
from .errors import LoaderError
from .unified_loader import UnifiedLoader


class DocumentLoaderFactory:
    """文档加载器工厂，统一使用 UnifiedLoader。"""

    def __init__(self) -> None:
        self._loader = UnifiedLoader()

    def get_loader(self, path: str | Path) -> DocumentLoader:
        """获取加载器。始终返回 UnifiedLoader。

        Args:
            path: 文件路径（仅用于校验存在性）。

        Returns:
            DocumentLoader: UnifiedLoader 实例。

        Raises:
            LoaderError: 文件不存在。
        """
        file_path = Path(path)
        if not file_path.exists():
            raise LoaderError(f"文件不存在: {path}", path=str(path))
        return self._loader

    def load(self, path: str | Path) -> LoadedDocument:
        """加载文档。

        Args:
            path: 文件路径。

        Returns:
            LoadedDocument: 已加载的文档对象。
        """
        return self._loader.load(path)

    def load_multiple(self, paths: list[str | Path]) -> list[LoadedDocument]:
        """批量加载多个文档。

        Args:
            paths: 文件路径列表。

        Returns:
            list[LoadedDocument]: 已加载的文档列表。
        """
        results: list[LoadedDocument] = []
        for path in paths:
            try:
                results.append(self._loader.load(path))
            except LoaderError as e:
                raise LoaderError(
                    f"加载文件失败: {path}", path=str(path), cause=e
                ) from e
        return results


# 全局默认工厂实例
_default_factory: DocumentLoaderFactory | None = None


def get_document_loader_factory() -> DocumentLoaderFactory:
    """获取全局默认的文档加载器工厂实例。"""
    global _default_factory
    if _default_factory is None:
        _default_factory = DocumentLoaderFactory()
    return _default_factory


def load_document(path: str | Path) -> LoadedDocument:
    """便捷函数：使用默认工厂加载文档。"""
    return get_document_loader_factory().load(path)


def load_documents(paths: list[str | Path]) -> list[LoadedDocument]:
    """便捷函数：批量加载多个文档。"""
    return get_document_loader_factory().load_multiple(paths)
