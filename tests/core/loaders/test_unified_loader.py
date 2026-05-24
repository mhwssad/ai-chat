"""测试 UnifiedLoader 统一文档加载器。"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ai.core.loaders.errors import LoaderError
from src.ai.core.loaders.unified_loader import UnifiedLoader


class TestUnifiedLoader:
    """测试 UnifiedLoader 类。"""

    @pytest.fixture
    def loader(self) -> UnifiedLoader:
        return UnifiedLoader()

    def test_load_text_file(self, loader: UnifiedLoader, tmp_path: Path) -> None:
        """测试加载纯文本文件。"""
        file = tmp_path / "test.txt"
        file.write_text("Hello, World!", encoding="utf-8")
        doc = loader.load(file)
        assert "Hello, World!" in doc.content
        assert doc.metadata.source_path == str(file.resolve())
        assert doc.metadata.title == "test.txt"

    def test_load_markdown_file(self, loader: UnifiedLoader, tmp_path: Path) -> None:
        """测试加载 Markdown 文件。"""
        file = tmp_path / "test.md"
        file.write_text("# Title\n\nContent here", encoding="utf-8")
        doc = loader.load(file)
        assert "Title" in doc.content
        assert "Content here" in doc.content

    def test_load_python_file(self, loader: UnifiedLoader, tmp_path: Path) -> None:
        """测试加载 Python 文件。"""
        file = tmp_path / "test.py"
        file.write_text("def hello():\n    print('test')", encoding="utf-8")
        doc = loader.load(file)
        assert "def hello()" in doc.content

    def test_load_json_file(self, loader: UnifiedLoader, tmp_path: Path) -> None:
        """测试加载 JSON 文件。

        unstructured 不支持任意 schema 的 JSON，会抛出 LoaderError。
        需要 JSON 解析的场景应使用 json.loads(load_document(path).content)。
        """
        file = tmp_path / "test.json"
        file.write_text('{"key": "value"}', encoding="utf-8")
        with pytest.raises(LoaderError):
            loader.load(file)

    def test_load_csv_file(self, loader: UnifiedLoader, tmp_path: Path) -> None:
        """测试加载 CSV 文件。"""
        file = tmp_path / "test.csv"
        file.write_text("name,value\ntest,123", encoding="utf-8")
        doc = loader.load(file)
        assert "name" in doc.content
        assert "test" in doc.content

    def test_load_nonexistent_file(self, loader: UnifiedLoader, tmp_path: Path) -> None:
        """测试加载不存在的文件。"""
        with pytest.raises(LoaderError) as exc_info:
            loader.load(tmp_path / "nonexistent.txt")
        assert "文件不存在" in str(exc_info.value)

    def test_load_directory_raises_error(self, loader: UnifiedLoader, tmp_path: Path) -> None:
        """测试加载目录时抛出错误。"""
        with pytest.raises(LoaderError) as exc_info:
            loader.load(tmp_path)
        assert "不是文件" in str(exc_info.value)

    def test_metadata_has_mime_type(self, loader: UnifiedLoader, tmp_path: Path) -> None:
        """测试元数据包含 MIME 类型。"""
        file = tmp_path / "test.txt"
        file.write_text("content", encoding="utf-8")
        doc = loader.load(file)
        assert doc.metadata.mime_type is not None
        assert "text" in doc.metadata.mime_type

    def test_metadata_has_size(self, loader: UnifiedLoader, tmp_path: Path) -> None:
        """测试元数据包含文件大小。"""
        content = "Hello, World!"
        file = tmp_path / "test.txt"
        file.write_text(content, encoding="utf-8")
        doc = loader.load(file)
        assert doc.metadata.size_bytes == len(content.encode("utf-8"))
