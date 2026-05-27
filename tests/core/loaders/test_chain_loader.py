"""测试 ChainLoader 职责链编排器。"""

from pathlib import Path
from collections.abc import Iterator

import pytest

from langchain_core.documents import Document

from src.ai.core.loaders.base import LoaderStrategy
from src.ai.core.loaders.chain_loader import ChainLoader
from src.ai.core.loaders.registry import LoaderRegistry
from src.ai.exception.loader_exception import LoaderError


# ── 测试用模拟加载器 ────────────────────────────────────────────────────────


class SuccessLoader(LoaderStrategy):
    """始终成功的加载器。"""

    def __init__(self, file_path: str, **kwargs) -> None:
        self._file_path = file_path

    def can_handle(self, file_path: Path) -> bool:
        return True

    def lazy_load(self) -> Iterator[Document]:
        yield Document(page_content="success", metadata={"loader": "success"})


class FailLoader(LoaderStrategy):
    """始终失败的加载器。"""

    def __init__(self, file_path: str, **kwargs) -> None:
        self._file_path = file_path

    def can_handle(self, file_path: Path) -> bool:
        return True

    def lazy_load(self) -> Iterator[Document]:
        raise RuntimeError("intentional failure")


class SkipLoader(LoaderStrategy):
    """can_handle 返回 False 的加载器。"""

    def __init__(self, file_path: str, **kwargs) -> None:
        self._file_path = file_path

    def can_handle(self, file_path: Path) -> bool:
        return False

    def lazy_load(self) -> Iterator[Document]:
        yield Document(page_content="skipped", metadata={})


class LoaderErrorLoader(LoaderStrategy):
    """抛出 LoaderError 的加载器（不应被吞掉）。"""

    def __init__(self, file_path: str, **kwargs) -> None:
        self._file_path = file_path

    def can_handle(self, file_path: Path) -> bool:
        return True

    def lazy_load(self) -> Iterator[Document]:
        raise LoaderError("config error", path=self._file_path)


# ── 测试 ────────────────────────────────────────────────────────────────────


class TestChainLoader:
    """测试 ChainLoader 编排器。"""

    def _make_registry(self, *loaders: type[LoaderStrategy]) -> LoaderRegistry:
        """创建包含指定加载器的注册表。"""
        registry = LoaderRegistry()
        for i, loader_cls in enumerate(loaders):
            registry.register(loader_cls, priority=(i + 1) * 100)
        return registry

    def test_first_success_wins(self, tmp_path: Path) -> None:
        """首个成功的加载器胜出。"""
        file = tmp_path / "test.txt"
        file.write_text("content", encoding="utf-8")
        registry = self._make_registry(SuccessLoader, FailLoader)
        loader = ChainLoader(str(file), registry)
        docs = loader.load()
        assert len(docs) == 1
        assert docs[0].page_content == "success"

    def test_skip_unsupported(self, tmp_path: Path) -> None:
        """can_handle=False 的加载器被跳过。"""
        file = tmp_path / "test.txt"
        file.write_text("content", encoding="utf-8")
        registry = self._make_registry(SkipLoader, SuccessLoader)
        loader = ChainLoader(str(file), registry)
        docs = loader.load()
        assert len(docs) == 1
        assert docs[0].page_content == "success"

    def test_fallback_on_failure(self, tmp_path: Path) -> None:
        """加载器失败时回退到下一个。"""
        file = tmp_path / "test.txt"
        file.write_text("content", encoding="utf-8")
        registry = self._make_registry(FailLoader, SuccessLoader)
        loader = ChainLoader(str(file), registry)
        docs = loader.load()
        assert len(docs) == 1
        assert docs[0].page_content == "success"

    def test_loader_error_not_swallowed(self, tmp_path: Path) -> None:
        """LoaderError 不被吞掉，直接向上抛出。"""
        file = tmp_path / "test.txt"
        file.write_text("content", encoding="utf-8")
        registry = self._make_registry(LoaderErrorLoader, SuccessLoader)
        loader = ChainLoader(str(file), registry)
        with pytest.raises(LoaderError) as exc_info:
            loader.load()
        assert "config error" in str(exc_info.value)

    def test_all_fail_raises_error(self, tmp_path: Path) -> None:
        """所有加载器都失败时抛出 LoaderError。"""
        file = tmp_path / "test.txt"
        file.write_text("content", encoding="utf-8")
        registry = self._make_registry(FailLoader)
        loader = ChainLoader(str(file), registry)
        with pytest.raises(LoaderError) as exc_info:
            loader.load()
        assert "所有加载策略均失败" in str(exc_info.value)

    def test_validation_before_chain(self, tmp_path: Path) -> None:
        """文件校验在职责链之前执行。"""
        registry = self._make_registry(SuccessLoader)
        loader = ChainLoader(str(tmp_path / "nonexistent.txt"), registry)
        with pytest.raises(LoaderError) as exc_info:
            loader.load()
        assert "文件不存在" in str(exc_info.value)

    def test_can_handle_always_true(self, tmp_path: Path) -> None:
        """编排器的 can_handle 始终返回 True。"""
        file = tmp_path / "test.txt"
        file.write_text("content", encoding="utf-8")
        loader = ChainLoader(str(file))
        assert loader.can_handle(Path("any.txt"))

    def test_real_loaders_integration(self, tmp_path: Path) -> None:
        """使用真实注册的加载器进行集成测试。"""
        from src.ai.core.loaders import loader_registry

        file = tmp_path / "test.txt"
        file.write_text("Hello, World!", encoding="utf-8")
        loader = ChainLoader(str(file), loader_registry)
        docs = loader.load()
        assert len(docs) >= 1
        assert any("Hello, World!" in d.page_content for d in docs)

    def test_real_loaders_markdown(self, tmp_path: Path) -> None:
        """真实加载器加载 Markdown 文件。"""
        from src.ai.core.loaders import loader_registry

        file = tmp_path / "test.md"
        file.write_text("# Title\n\nContent", encoding="utf-8")
        loader = ChainLoader(str(file), loader_registry)
        docs = loader.load()
        assert len(docs) >= 1


class TestChainLoaderImports:
    """测试模块级导入。"""

    def test_import_all_public_api(self) -> None:
        """验证所有公共 API 可导入。"""
        from src.ai.core.loaders import (
            ChainLoader,
            FileValidator,
            LoaderError,
            LoaderRegistry,
            LoaderStrategy,
            LoadPermissionError,
            OcrImageLoader,
            PlainTextLoader,
            UnstructuredLoader,
            UnstructuredSettings,
            UnsupportedFileTypeError,
            loader_registry,
            unstructured_settings,
        )

        assert ChainLoader is not None
        assert LoaderStrategy is not None
        assert LoaderRegistry is not None
        assert loader_registry is not None
