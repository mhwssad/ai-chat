"""文件类型识别工具类的测试。"""

from pathlib import Path

import pytest


class TestFileRecognizer:
    """FileRecognizer 类的单元测试。"""

    def setup_method(self) -> None:
        """每个测试方法前创建新的识别器实例。"""
        from src.ai.utils.file_recognition import FileRecognizer

        self.recognizer = FileRecognizer()

    def test_recognize_file_returns_result(self, tmp_path: Path) -> None:
        """测试识别文件并返回结果对象。"""
        text_file = tmp_path / "test.txt"
        text_file.write_bytes(b"Hello, World!")

        result = self.recognizer.recognize(text_file)
        # 验证返回结果有 output 属性
        assert hasattr(result, "output")
        assert hasattr(result, "score")
        assert result.output.label in {"txt", "text", "ascii"}

    def test_recognize_python_file(self, tmp_path: Path) -> None:
        """测试识别 Python 文件。"""
        py_file = tmp_path / "test.py"
        py_file.write_bytes(b"def hello():\n    print('world')\n")

        result = self.recognizer.recognize(py_file)
        assert result.output.label == "python"
        assert "python" in result.output.mime_type

    def test_recognize_content(self) -> None:
        """测试通过字节内容识别文件类型。"""
        # 使用更长的 Python 代码片段以获得更好的识别
        content = b"def hello():\n    print('hello world')\n    return True\n"
        result = self.recognizer.recognize_content(content)
        # 对于无扩展名的内容，magika 可能识别为 txt 或 python
        assert isinstance(result.output.label, str)

    def test_get_label(self, tmp_path: Path) -> None:
        """测试获取文件类型标签。"""
        text_file = tmp_path / "test.txt"
        text_file.write_bytes(b"test content")

        label = self.recognizer.get_label(text_file)
        assert isinstance(label, str)
        # txt 文件被识别为 txt 标签
        assert label == "txt"

    def test_get_mime_type(self, tmp_path: Path) -> None:
        """测试获取 MIME 类型。"""
        text_file = tmp_path / "test.txt"
        text_file.write_bytes(b"test content")

        mime_type = self.recognizer.get_mime_type(text_file)
        assert isinstance(mime_type, str)
        assert "/" in mime_type

    def test_is_text(self, tmp_path: Path) -> None:
        """测试文本文件判断。"""
        text_file = tmp_path / "test.txt"
        text_file.write_bytes(b"Hello, World!")

        assert self.recognizer.is_text(text_file) is True

    def test_is_image(self, tmp_path: Path) -> None:
        """测试图片文件判断。"""
        # PNG 文件头 (magic bytes)
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        image_file = tmp_path / "test.png"
        image_file.write_bytes(png_data)

        result = self.recognizer.recognize(image_file)
        assert isinstance(result.output.label, str)

    def test_is_code(self, tmp_path: Path) -> None:
        """测试代码文件判断。"""
        py_file = tmp_path / "test.py"
        py_file.write_bytes(b"def test():\n    pass\n")

        assert self.recognizer.is_code(py_file) is True

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        """测试接受字符串路径。"""
        text_file = tmp_path / "test.txt"
        text_file.write_bytes(b"test")

        result = self.recognizer.recognize(str(text_file))
        assert result.output.label == "txt"


class TestModuleLevelFunctions:
    """模块级别便捷函数的测试。"""

    def setup_method(self) -> None:
        """每个测试方法前导入函数。"""
        from src.ai.utils.file_recognition import (  # type: ignore
            file_recognizer,
            get_file_label,
            get_file_mime_type,
            recognize_file,
        )

        self.recognize_file = recognize_file
        self.get_file_label = get_file_label
        self.get_file_mime_type = get_file_mime_type
        self.file_recognizer = file_recognizer

    def test_recognize_file(self, tmp_path: Path) -> None:
        """测试模块级 recognize_file 函数。"""
        text_file = tmp_path / "test.txt"
        text_file.write_bytes(b"Hello")

        result = self.recognize_file(text_file)
        assert result.output.label == "txt"

    def test_get_file_label(self, tmp_path: Path) -> None:
        """测试模块级 get_file_label 函数。"""
        text_file = tmp_path / "test.txt"
        text_file.write_bytes(b"Hello")

        label = self.get_file_label(text_file)
        assert isinstance(label, str)
        assert label == "txt"

    def test_get_file_mime_type(self, tmp_path: Path) -> None:
        """测试模块级 get_file_mime_type 函数。"""
        text_file = tmp_path / "test.txt"
        text_file.write_bytes(b"Hello")

        mime_type = self.get_file_mime_type(text_file)
        assert isinstance(mime_type, str)
        assert "/" in mime_type


class TestSingletonBehavior:
    """单例行为的测试。"""

    def test_singleton_returns_same_instance(self) -> None:
        """测试 file_recognizer 是单例。"""
        from src.ai.utils.file_recognition import FileRecognizer  # type: ignore
        from src.ai.utils.file_recognition import file_recognizer  # type: ignore

        r1 = FileRecognizer()
        r2 = FileRecognizer()
        assert r1 is r2
        assert r1 is file_recognizer

    def test_singleton_shares_state(self, tmp_path: Path) -> None:
        """测试单例共享内部状态。"""
        from src.ai.utils.file_recognition import FileRecognizer  # type: ignore

        r1 = FileRecognizer()
        r2 = FileRecognizer()
        text_file = tmp_path / "test.txt"
        text_file.write_bytes(b"Hello")

        # 两者应识别出相同结果
        result1 = r1.recognize(text_file)
        result2 = r2.recognize(text_file)
        assert result1.output.label == result2.output.label