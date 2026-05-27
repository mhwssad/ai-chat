"""文档加载器错误类。"""


from pathlib import Path

from src.ai.exception.base_exception import BaseExceptions


class LoaderError(BaseExceptions):
    """文档加载失败。"""

    def __init__(self, message: str, *, path: str | None = None, cause: Exception | None = None) -> None:
        """初始化加载器错误。

        Args:
            message: 错误消息。
            path: 失败的文件路径。
            cause: 原始异常。
        """
        context = {}
        if path:
            context["path"] = str(path)
        if cause:
            context["cause"] = str(cause)
        super().__init__(message, context=context if context else None)
        self.path = path
        self.cause = cause


class UnsupportedFileTypeError(LoaderError):
    """不支持的文件类型错误。"""

    def __init__(self, path: str | Path, *, supported_types: list[str] | None = None) -> None:
        """初始化不支持文件类型错误。

        Args:
            path: 文件路径。
            supported_types: 支持的文件类型列表。
        """
        path_str = str(path)
        context: dict[str, str | list[str]] = {"path": path_str}
        if supported_types:
            context["supported_types"] = supported_types
        message = f"不支持的文件类型: {Path(path).suffix or 'unknown'}"
        super().__init__(message, path=path_str, cause=None)
        self.supported_types = supported_types


class LoadPermissionError(LoaderError):
    """文件读取权限错误。"""

    def __init__(self, path: str | Path) -> None:
        """初始化权限错误。

        Args:
            path: 文件路径。
        """
        super().__init__(f"无权限读取文件: {path}", path=str(path))
