"""测试 OcrImageLoader 图片 OCR 加载器。"""

from pathlib import Path

import pytest

from src.ai.core.loaders.ocr_loader import OcrImageLoader


class TestOcrImageLoader:
    """测试 OcrImageLoader 类。"""

    def test_can_handle_image_extensions(self) -> None:
        loader = OcrImageLoader("dummy.png")
        for ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif"]:
            assert loader.can_handle(Path(f"file{ext}"))

    def test_can_handle_non_image(self) -> None:
        loader = OcrImageLoader("dummy.txt")
        assert not loader.can_handle(Path("file.txt"))
        assert not loader.can_handle(Path("file.pdf"))

    def test_can_handle_case_insensitive(self) -> None:
        loader = OcrImageLoader("dummy.PNG")
        assert loader.can_handle(Path("file.PNG"))
        assert loader.can_handle(Path("file.Jpg"))

    def test_load_nonexistent_image(self, tmp_path: Path) -> None:
        loader = OcrImageLoader(str(tmp_path / "nonexistent.png"))
        with pytest.raises(Exception):
            loader.load()

    def test_load_text_as_image_fails(self, tmp_path: Path) -> None:
        file = tmp_path / "fake.png"
        file.write_text("not an image", encoding="utf-8")
        loader = OcrImageLoader(str(file))
        with pytest.raises(Exception):
            loader.load()
