"""加载器策略抽象基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

from src.ai.exception.loader_exception import LoaderError


class LoaderStrategy(ABC):
    """加载器策略基类。

    所有加载器继承此类，实现 can_handle() 和 _load_single()。
    基类提供 load_file() / load_dir() / load_batch() 三种便捷加载方式。
    """

    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """判断本策略能否处理该文件。

        Args:
            file_path: 文件路径。

        Returns:
            True 表示可以处理，False 表示跳过。
        """

    @abstractmethod
    def _load_single(self, file_path: Path) -> list[Document]:
        """加载单个文件，返回 Document 列表。

        Args:
            file_path: 已校验过的文件路径。

        Returns:
            Document 列表。
        """

    def load_file(self, path: str | Path) -> list[Document]:
        """加载单个文件。

        Args:
            path: 文件路径。

        Returns:
            Document 列表。

        Raises:
            LoaderError: 文件校验失败或加载失败时抛出。
        """
        file_path = Path(path)
        self._validate(file_path)
        return self._load_single(file_path)

    def load_dir(
        self, dir_path: str | Path, *, recursive: bool = False
    ) -> list[Document]:
        """加载目录下所有可处理的文件。

        Args:
            dir_path: 目录路径。
            recursive: 是否递归遍历子目录。

        Returns:
            Document 列表。

        Raises:
            LoaderError: 目录不存在时抛出。
        """
        dir_path = Path(dir_path)
        self._validate_dir(dir_path)
        docs: list[Document] = []
        pattern = "**/*" if recursive else "*"
        for f in sorted(dir_path.glob(pattern)):
            if f.is_file() and self.can_handle(f):
                docs.extend(self._load_single(f))
        return docs

    def load_batch(self, paths: list[str | Path]) -> list[Document]:
        """批量加载多个文件。

        Args:
            paths: 文件路径列表。

        Returns:
            Document 列表。
        """
        docs: list[Document] = []
        for p in paths:
            docs.extend(self.load_file(p))
        return docs

    def _validate(self, file_path: Path) -> None:
        """校验单个文件。

        Args:
            file_path: 文件路径。

        Raises:
            LoaderError: 文件不存在、不是文件时抛出。
        """
        if not file_path.exists():
            raise LoaderError(f"文件不存在: {file_path}", path=str(file_path))
        if not file_path.is_file():
            raise LoaderError(f"不是文件: {file_path}", path=str(file_path))

    def _validate_dir(self, dir_path: Path) -> None:
        """校验目录。

        Args:
            dir_path: 目录路径。

        Raises:
            LoaderError: 目录不存在或不是目录时抛出。
        """
        if not dir_path.exists():
            raise LoaderError(f"目录不存在: {dir_path}", path=str(dir_path))
        if not dir_path.is_dir():
            raise LoaderError(f"不是目录: {dir_path}", path=str(dir_path))


class LangchainAdapter(BaseLoader):
    """将 LoaderStrategy 适配为 langchain BaseLoader。

    用于需要将加载器传入 langchain 链/Agent 的场景。

    Args:
        strategy: LoaderStrategy 实例。
        file_path: 要加载的文件路径。
    """

    def __init__(self, strategy: LoaderStrategy, file_path: str) -> None:
        self._strategy = strategy
        self._file_path = file_path

    def lazy_load(self) -> Iterator[Document]:
        yield from self._strategy._load_single(Path(self._file_path))
