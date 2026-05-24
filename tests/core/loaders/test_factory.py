"""测试 DocumentLoaderFactory 工厂类。"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ai.core.loaders.errors import LoaderError
from src.ai.core.loaders.factory import (
    DocumentLoaderFactory,
    get_document_loader_factory,
    load_document,
    load_documents,
)
from src.ai.core.loaders.unified_loader import UnifiedLoader


class TestDocumentLoaderFactory:
    """测试 DocumentLoaderFactory 类。"""

    @pytest.fixture
    def factory(self) -> DocumentLoaderFactory:
        return DocumentLoaderFactory()

    def test_get_loader_returns_unified_loader(
        self, factory: DocumentLoaderFactory, tmp_path: Path
    ) -> None:
        """测试 get_loader 始终返回 UnifiedLoader。"""
        file = tmp_path / "test.txt"
        file.write_text("Hello")
        loader = factory.get_loader(file)
        assert isinstance(loader, UnifiedLoader)

    def test_load_text_file(
        self, factory: DocumentLoaderFactory, tmp_path: Path
    ) -> None:
        """测试工厂加载文本文件。"""
        file = tmp_path / "test.txt"
        file.write_text("Hello, World!", encoding="utf-8")
        doc = factory.load(file)
        assert "Hello, World!" in doc.content

    def test_load_markdown_file(
        self, factory: DocumentLoaderFactory, tmp_path: Path
    ) -> None:
        """测试工厂加载 Markdown 文件。"""
        file = tmp_path / "test.md"
        file.write_text("# Title\n\nContent")
        doc = factory.load(file)
        assert "Title" in doc.content

    def test_load_nonexistent_file(
        self, factory: DocumentLoaderFactory, tmp_path: Path
    ) -> None:
        """测试加载不存在的文件。"""
        with pytest.raises(LoaderError) as exc_info:
            factory.load(tmp_path / "nonexistent.txt")
        assert "文件不存在" in str(exc_info.value)

    def test_load_multiple_files(
        self, factory: DocumentLoaderFactory, tmp_path: Path
    ) -> None:
        """测试批量加载文件。"""
        files = []
        for ext, content in [
            ("txt", "Text"),
            ("md", "# Markdown"),
            ("py", "print('hello')"),
        ]:
            f = tmp_path / f"test.{ext}"
            f.write_text(content)
            files.append(f)
        docs = factory.load_multiple(files)
        assert len(docs) == 3


class TestConvenienceFunctions:
    """测试便捷函数。"""

    def test_load_document_function(self, tmp_path: Path) -> None:
        """测试 load_document 便捷函数。"""
        file = tmp_path / "test.txt"
        file.write_text("Hello", encoding="utf-8")
        doc = load_document(file)
        assert "Hello" in doc.content

    def test_load_documents_function(self, tmp_path: Path) -> None:
        """测试 load_documents 便捷函数。"""
        files = []
        for i in range(3):
            f = tmp_path / f"test_{i}.txt"
            f.write_text(f"Content {i}")
            files.append(f)
        docs = load_documents(files)
        assert len(docs) == 3

    def test_get_document_loader_factory(self) -> None:
        """测试获取全局默认工厂实例。"""
        factory1 = get_document_loader_factory()
        factory2 = get_document_loader_factory()
        assert factory1 is factory2
