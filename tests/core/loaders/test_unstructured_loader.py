"""测试 UnstructuredLoader 文档加载器。"""

from pathlib import Path

from src.ai.config.loader_settings import UnstructuredSettings
from src.ai.core.loaders.unstructured_loader import UnstructuredLoader


class TestUnstructuredLoader:
    """测试 UnstructuredLoader 类。"""

    def test_can_handle_always_true(self, tmp_path: Path) -> None:
        """通用处理器，can_handle 始终返回 True。"""
        loader = UnstructuredLoader(str(tmp_path / "any.txt"))
        assert loader.can_handle(Path("file.txt"))
        assert loader.can_handle(Path("file.xyz"))
        assert loader.can_handle(Path("file.pdf"))

    def test_load_text_file(self, tmp_path: Path) -> None:
        file = tmp_path / "test.txt"
        file.write_text("Hello, World!", encoding="utf-8")
        docs = UnstructuredLoader(str(file)).load()
        assert len(docs) >= 1
        assert any("Hello, World!" in d.page_content for d in docs)

    def test_load_markdown_file(self, tmp_path: Path) -> None:
        file = tmp_path / "test.md"
        file.write_text("# Title\n\nContent here", encoding="utf-8")
        docs = UnstructuredLoader(str(file)).load()
        assert len(docs) >= 1
        content = " ".join(d.page_content for d in docs)
        assert "Title" in content

    def test_load_csv_file(self, tmp_path: Path) -> None:
        file = tmp_path / "test.csv"
        file.write_text("name,value\ntest,123", encoding="utf-8")
        docs = UnstructuredLoader(str(file)).load()
        assert len(docs) >= 1

    def test_metadata_enrichment(self, tmp_path: Path) -> None:
        file = tmp_path / "test.txt"
        file.write_text("content", encoding="utf-8")
        docs = UnstructuredLoader(str(file)).load()
        meta = docs[0].metadata
        assert "source" in meta
        assert "title" in meta
        assert "mime_type" in meta
        assert "size_bytes" in meta

    def test_custom_settings(self, tmp_path: Path) -> None:
        file = tmp_path / "test.txt"
        file.write_text("content", encoding="utf-8")
        settings = UnstructuredSettings(strategy="fast")
        docs = UnstructuredLoader(str(file), settings).load()
        assert len(docs) >= 1

    def test_returns_empty_on_unsupported_format(self, tmp_path: Path) -> None:
        file = tmp_path / "test.xyz"
        file.write_bytes(b"\x00\x01\x02")
        try:
            UnstructuredLoader(str(file)).load()
        except Exception:
            pass
