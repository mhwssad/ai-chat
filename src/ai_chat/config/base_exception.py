"""
核心基础异常类

提供通用的异常基类，支持灵活的错误消息格式化、上下文信息和异常链。
所有模块的自定义异常应继承自此类或其子类。
"""

from typing import Any, Optional, Dict


class BaseExceptions(Exception):
    """
    核心基础异常类

    提供增强的异常处理能力，包括：
    - 结构化的错误消息
    - 灵活的上下文信息存储
    - 异常链支持（保留原始异常）
    - 详细的错误信息获取

    Attributes:
        _message: 原始错误消息
        _context: 上下文信息字典
        _original_exception: 原始异常对象（可选）
        _error_code: 错误代码（可选）

    Example:
        >>> try:
        ...     raise ValueError("原始错误")
        ... except ValueError as e:
        ...     raise BaseExceptions("包装后的错误", error_code="ERR_001") from e
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ) -> None:
        """
        初始化基础异常

        Args:
            message: 错误消息（必需）
            context: 上下文信息字典（可选），用于存储额外的错误相关信息
            error_code: 错误代码（可选），用于错误分类和追踪

        Example:
            >>> exc = BaseExceptions("文件不存在", {"file": "test.txt", "path": "/tmp"})
            >>> print(exc)
            文件不存在 [file=test.txt, path=/tmp]
        """
        super().__init__(message)
        self._message = message
        self._context: Dict[str, Any] = context or {}
        self._error_code = error_code

        # 保留原始异常（如果有）
        self._original_exception: Optional[Exception] = None

    @property
    def message(self) -> str:
        """
        获取原始错误消息

        Returns:
            错误消息字符串
        """
        return self._message

    @property
    def context(self) -> Dict[str, Any]:
        """
        获取上下文信息

        Returns:
            上下文信息字典的副本
        """
        return self._context.copy()

    @property
    def error_code(self) -> Optional[str]:
        """
        获取错误代码

        Returns:
            错误代码字符串，如果未设置则返回 None
        """
        return self._error_code

    @property
    def original_exception(self) -> Optional[Exception]:
        """
        获取原始异常

        Returns:
            原始异常对象，如果不存在则返回 None
        """
        return self._original_exception

    def add_context(self, key: str, value: Any) -> None:
        """
        添加上下文信息

        Args:
            key: 上下文键名
            value: 上下文值

        Example:
            >>> exc = BaseExceptions("处理失败")
            >>> exc.add_context("file", "data.txt")
            >>> exc.add_context("line", 42)
            >>> print(exc.context)
            {'file': 'data.txt', 'line': 42}
        """
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """
        获取指定的上下文信息

        Args:
            key: 上下文键名
            default: 默认值，当键不存在时返回

        Returns:
            上下文值，如果键不存在则返回默认值
        """
        return self._context.get(key, default)

    def has_context(self, key: str) -> bool:
        """
        检查是否存在指定的上下文信息

        Args:
            key: 上下文键名

        Returns:
            如果键存在返回 True，否则返回 False
        """
        return key in self._context

    def set_original_exception(self, exc: Exception) -> None:
        """
        设置原始异常（通常由异常链自动设置）

        Args:
            exc: 原始异常对象
        """
        self._original_exception = exc

    def get_details(self) -> Dict[str, Any]:
        """
        获取异常的详细信息

        Returns:
            包含错误消息、错误代码、上下文信息和原始异常的字典

        Example:
            >>> exc = BaseExceptions("错误", {"key": "value"}, "ERR_001")
            >>> details = exc.get_details()
            >>> print(details)
            {'error': '错误', 'error_code': 'ERR_001', 'context': {'key': 'value'}}
        """
        details: Dict[str, Any] = {
            "error": self._message,
            "context": self._context,
        }

        if self._error_code:
            details["error_code"] = self._error_code

        if self._original_exception:
            details["original_error"] = {
                "type": type(self._original_exception).__name__,
                "message": str(self._original_exception),
            }

        return details

    def _format_message(self) -> str:
        """
        格式化错误消息

        Returns:
            格式化后的错误消息字符串
        """
        # 如果有错误代码，添加到消息前面
        if self._error_code:
            formatted = f"[{self._error_code}] {self._message}"
        else:
            formatted = self._message

        # 如果有上下文信息，添加到消息后面
        if self._context:
            context_str = ", ".join(f"{k}={v}" for k, v in self._context.items())
            formatted = f"{formatted} [{context_str}]"

        return formatted

    def __str__(self) -> str:
        """
        返回格式化的错误信息

        Returns:
            格式化后的错误消息字符串
        """
        return self._format_message()

    def __repr__(self) -> str:
        """
        返回异常的开发者表示

        Returns:
            异常类的字符串表示
        """
        class_name = self.__class__.__name__
        msg = f"{class_name}(message={self._message!r}"

        if self._error_code:
            msg += f", error_code={self._error_code!r}"

        if self._context:
            msg += f", context={self._context!r}"

        msg += ")"
        return msg
