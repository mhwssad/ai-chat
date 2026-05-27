"""文件类型识别工具类，使用 magika 库进行基于深度学习的文件类型检测。"""

from pathlib import Path
from typing import Any, Union

from magika import Magika

from src.ai.utils.obj import singleton


@singleton
class FileRecognizer:
    """文件类型识别器，使用 magika 进行文件类型检测。

    基于深度学习的文件类型识别工具，支持通过文件内容（而非扩展名）
    来准确识别文件的 MIME 类型和分类。

    示例:
        ```python
        recognizer = FileRecognizer()
        # 识别文件路径
        result = recognizer.recognize("/path/to/file.txt")
        print(result.output.label)  # 输出: text

        # 识别文件内容
        result = recognizer.recognize_content(b"Hello, World!")
        print(result.output.label)  # 输出: text
        ```
    """

    def __init__(self) -> None:
        """初始化 magika 识别器。"""
        self._magika = Magika()

    def recognize(self, path: Union[str, Path]) -> Any:
        """识别指定路径文件的类型。

        Args:
            path: 文件路径，可以是字符串或 Path 对象。

        Returns:
            包含识别结果的 MagikaResult 对象，包含以下属性:
                - output: ContentTypeInfo 对象，含 label、mime_type 等
                - prediction: MagikaPrediction 对象，含 score 等
        """
        path = Path(path)
        return self._magika.identify_path(path)

    def recognize_content(self, content: bytes) -> Any:
        """识别给定字节内容的文件类型。

        Args:
            content: 文件内容的字节数据。

        Returns:
            包含识别结果的 MagikaResult 对象。
        """
        return self._magika.identify_bytes(content)

    def get_label(self, path: str | Path) -> str:
        """获取文件的类型标签。

        Args:
            path: 文件路径。

        Returns:
            文件类型标签字符串。
        """
        result = self.recognize(path)
        return result.output.label

    def get_mime_type(self, path: str | Path) -> str:
        """获取文件的 MIME 类型。

        Args:
            path: 文件路径。

        Returns:
            MIME 类型字符串。
        """
        result = self.recognize(path)
        return result.output.mime_type

    def is_text(self, path: str | Path) -> bool:
        """判断文件是否为文本类型。

        Args:
            path: 文件路径。

        Returns:
            如果文件是文本类型返回 True，否则返回 False。
        """
        result = self.recognize(path)
        return result.output.label in {
            "text",
            "ascii",
            "txt",
            "json",
            "jsonl",
            "xml",
            "html",
            "markdown",
            "yaml",
            "toml",
            "config",
        }

    def is_image(self, path: str | Path) -> bool:
        """判断文件是否为图片类型。

        Args:
            path: 文件路径。

        Returns:
            如果文件是图片类型返回 True，否则返回 False。
        """
        result = self.recognize(path)
        return result.output.label in {
            "png",
            "jpeg",
            "gif",
            "bmp",
            "webp",
            "svg",
            "ico",
        }

    def is_code(self, path: str | Path) -> bool:
        """判断文件是否为代码类型。

        Args:
            path: 文件路径。

        Returns:
            如果文件是代码类型返回 True，否则返回 False。
        """
        result = self.recognize(path)
        code_labels = {
            "python",
            "javascript",
            "typescript",
            "java",
            "c",
            "cpp",
            "csharp",
            "go",
            "rust",
            "ruby",
            "php",
            "swift",
            "kotlin",
            "shell",
            "powershell",
            "html",
            "css",
            "sql",
            "json",
            "yaml",
            "toml",
            "xml",
        }
        return result.output.label in code_labels

    def is_binary(self, path: str | Path) -> bool:
        """判断文件是否为二进制类型。

        Args:
            path: 文件路径。

        Returns:
            如果文件是二进制类型返回 True，否则返回 False。
        """
        result = self.recognize(path)
        return result.output.label in {
            "binary",
            "image",
            "audio",
            "video",
            "archive",
            "document",
            "spreadsheet",
            "presentation",
            "unknown",  # 无法识别时当作二进制处理，回退到 Base64
        }

    def is_audio(self, path: str | Path) -> bool:
        """判断文件是否为音频类型。

        Args:
            path: 文件路径。

        Returns:
            如果文件是音频类型返回 True，否则返回 False。
        """
        result = self.recognize(path)
        return result.output.label == "audio"

    def is_video(self, path: str | Path) -> bool:
        """判断文件是否为视频类型。

        Args:
            path: 文件路径。

        Returns:
            如果文件是视频类型返回 True，否则返回 False。
        """
        result = self.recognize(path)
        return result.output.label == "video"


# 全局单例实例，供模块级别使用
file_recognizer = FileRecognizer()


def recognize_file(path: str | Path) -> Any:
    """便捷函数：识别文件类型。

    Args:
        path: 文件路径。

    Returns:
        MagikaResult 识别结果对象。
    """
    return file_recognizer.recognize(path)


def get_file_label(path: str | Path) -> str:
    """便捷函数：获取文件类型标签。

    Args:
        path: 文件路径。

    Returns:
        文件类型标签字符串。
    """
    return file_recognizer.get_label(path)


def get_file_mime_type(path: str | Path) -> str:
    """便捷函数：获取文件 MIME 类型。

    Args:
        path: 文件路径。

    Returns:
        MIME 类型字符串。
    """
    return file_recognizer.get_mime_type(path)