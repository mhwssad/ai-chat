"""测试 PlainTextLoader 纯文本加载器。"""

from pathlib import Path

from src.ai.core.loaders.text_loader import PlainTextLoader


class TestPlainTextLoader:
    """测试 PlainTextLoader 类。"""

    def test_can_handle_always_true(self, tmp_path: Path) -> None:
        """兜底策略，can_handle 始终返回 True。"""
        loader = PlainTextLoader(str(tmp_path / "any.txt"))
        assert loader.can_handle(Path("file.txt"))
        assert loader.can_handle(Path("file.xyz"))

    def test_load_utf8_file(self, tmp_path: Path) -> None:
        file = tmp_path / "test.txt"
        file.write_text("你好世界", encoding="utf-8")
        docs = PlainTextLoader(str(file)).load()
        assert len(docs) == 1
        assert "你好世界" in docs[0].page_content
        assert docs[0].metadata["source"] == str(file.resolve())

    def test_load_gbk_file(self, tmp_path: Path) -> None:
        file = tmp_path / "test.txt"
        file.write_text("中文内容", encoding="gbk")
        docs = PlainTextLoader(str(file)).load()
        assert len(docs) == 1
        assert "中文内容" in docs[0].page_content

    def test_metadata_fields(self, tmp_path: Path) -> None:
        file = tmp_path / "test.txt"
        file.write_text("content", encoding="utf-8")
        docs = PlainTextLoader(str(file)).load()
        meta = docs[0].metadata
        assert meta["title"] == "test.txt"
        assert meta["mime_type"] == "text/plain"
        assert meta["size_bytes"] == len("content".encode("utf-8"))
        assert meta["file_label"] == "text"
        assert meta["page_count"] == 1
        assert meta["fallback"] is True

    def test_load_binary_fallback(self, tmp_path: Path) -> None:
        file = tmp_path / "test.bin"
        file.write_bytes(b"\x80\x81\x82")
        docs = PlainTextLoader(str(file)).load()
        assert len(docs) == 1
        assert docs[0].page_content is not None

    def test_custom_encodings(self, tmp_path: Path) -> None:
        file = tmp_path / "test.txt"
        file.write_text("test", encoding="utf-8")
        docs = PlainTextLoader(str(file), encodings=["utf-8"]).load()
        assert len(docs) == 1
