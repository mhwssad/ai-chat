"""测试 FileValidator 文件校验器。"""

from pathlib import Path

import pytest

from src.ai.core.loaders.validators import FileValidator
from src.ai.exception.loader_exception import LoaderError


class TestFileValidator:
    """测试 FileValidator 类。"""

    @pytest.fixture
    def validator(self) -> FileValidator:
        return FileValidator(max_file_size=1024)

    def test_validate_existing_file(self, validator: FileValidator, tmp_path: Path) -> None:
        """校验存在的文件应通过。"""
        file = tmp_path / "test.txt"
        file.write_text("hello", encoding="utf-8")
        validator.validate(file)

    def test_validate_nonexistent_file(self, validator: FileValidator, tmp_path: Path) -> None:
        """校验不存在的文件应抛 LoaderError。"""
        with pytest.raises(LoaderError) as exc_info:
            validator.validate(tmp_path / "nonexistent.txt")
        assert "文件不存在" in str(exc_info.value)

    def test_validate_directory(self, validator: FileValidator, tmp_path: Path) -> None:
        """校验目录应抛 LoaderError。"""
        with pytest.raises(LoaderError) as exc_info:
            validator.validate(tmp_path)
        assert "不是文件" in str(exc_info.value)

    def test_validate_file_too_large(self, tmp_path: Path) -> None:
        """校验超过大小限制的文件应抛 LoaderError。"""
        validator = FileValidator(max_file_size=5)
        file = tmp_path / "large.txt"
        file.write_text("exceeds five bytes", encoding="utf-8")
        with pytest.raises(LoaderError) as exc_info:
            validator.validate(file)
        assert "文件过大" in str(exc_info.value)

    def test_validate_file_at_limit(self, tmp_path: Path) -> None:
        """校验恰好在大小限制内的文件应通过。"""
        validator = FileValidator(max_file_size=5)
        file = tmp_path / "exact.txt"
        file.write_text("12345", encoding="utf-8")
        validator.validate(file)
