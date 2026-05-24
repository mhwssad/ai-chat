"""测试文档加载器的基础类和接口。"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ai.core.loaders.base import DocumentMetadata, DocumentLoader, LoadedDocument
from src.ai.core.loaders.errors import LoaderError


class TestDocumentMetadata:
    """测试 DocumentMetadata 数据类。"""

    def test_create_minimal_metadata(self) -> None:
        """测试创建最小元数据。"""
        metadata = DocumentMetadata(source_path="/path/to/file.txt")
        assert metadata.source_path == "/path/to/file.txt"
        assert metadata.title is None
        assert metadata.mime_type is None
        assert metadata.size_bytes is None
        assert metadata.file_label is None
        assert metadata.extra == {}

    def test_create_full_metadata(self) -> None:
        """测试创建完整元数据。"""
        metadata = DocumentMetadata(
            source_path="/path/to/file.txt",
            title="测试文件",
            mime_type="text/plain",
            size_bytes=1024,
            file_label="text",
            extra={"author": "测试者"},
        )
        assert metadata.source_path == "/path/to/file.txt"
        assert metadata.title == "测试文件"
        assert metadata.mime_type == "text/plain"
        assert metadata.size_bytes == 1024
        assert metadata.file_label == "text"
        assert metadata.extra == {"author": "测试者"}

    def test_metadata_is_frozen(self) -> None:
        """测试元数据是不可变的。"""
        metadata = DocumentMetadata(source_path="/path/to/file.txt")
        with pytest.raises(Exception):  # frozen dataclass should raise error
            metadata.source_path = "/other/path"  # type: ignore


class TestLoadedDocument:
    """测试 LoadedDocument 数据类。"""

    def test_create_loaded_document(self) -> None:
        """测试创建已加载文档对象。"""
        metadata = DocumentMetadata(
            source_path="/path/to/file.txt",
            title="测试文件",
        )
        doc = LoadedDocument(
            content="Hello, World!",
            metadata=metadata,
        )
        assert doc.content == "Hello, World!"
        assert doc.metadata.title == "测试文件"

    def test_loaded_document_is_frozen(self) -> None:
        """测试已加载文档是不可变的。"""
        metadata = DocumentMetadata(source_path="/path/to/file.txt")
        doc = LoadedDocument(content="test", metadata=metadata)
        with pytest.raises(Exception):  # frozen dataclass should raise error
            doc.content = "other"  # type: ignore


class MockDocumentLoader(DocumentLoader):
    """模拟文档加载器用于测试。"""

    def load(self, path: str | Path) -> LoadedDocument:
        """模拟加载方法。"""
        file_path = Path(path)
        return LoadedDocument(
            content=f"Content of {file_path.name}",
            metadata=DocumentMetadata(
                source_path=str(file_path.resolve()),
                title=file_path.name,
            ),
        )


class TestDocumentLoader:
    """测试 DocumentLoader 抽象基类。"""

    def test_load_multiple(self, tmp_path: Path) -> None:
        """测试批量加载功能。"""
        # 创建测试文件
        files = []
        for i in range(3):
            f = tmp_path / f"test_{i}.txt"
            f.write_text(f"Content {i}", encoding="utf-8")
            files.append(f)

        loader = MockDocumentLoader()
        docs = loader.load_multiple(files)

        assert len(docs) == 3
        for i, doc in enumerate(docs):
            # MockDocumentLoader 返回 "Content of test_N.txt"
            assert f"test_{i}.txt" in doc.content


class TestLoaderError:
    """测试 LoaderError 错误类。"""

    def test_create_error_with_message(self) -> None:
        """测试创建带消息的错误。"""
        error = LoaderError("测试错误")
        assert error.message == "测试错误"
        assert "测试错误" in str(error)

    def test_create_error_with_path(self) -> None:
        """测试创建带路径的错误。"""
        error = LoaderError("文件加载失败", path="/path/to/file.txt")
        assert error.path == "/path/to/file.txt"

    def test_create_error_with_cause(self) -> None:
        """测试创建带原始异常的错误。"""
        cause = ValueError("原始错误")
        error = LoaderError("包装错误", cause=cause)
        assert error.cause is cause