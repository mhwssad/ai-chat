"""RAG 和文本切割异常。"""

from src.ai.exception.base_exception import BaseExceptions


class RagError(BaseExceptions):
    """RAG 操作失败。"""


class RagEmbeddingError(BaseExceptions):
    """RAG embedding 失败。"""


class SplitterError(BaseExceptions):
    """文本切割失败。"""

    def __init__(
        self,
        message: str,
        *,
        strategy: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """初始化切割器错误。

        Args:
            message: 错误消息。
            strategy: 使用的切割策略名称。
            cause: 原始异常。
        """
        context: dict[str, str] = {}
        if strategy:
            context["strategy"] = strategy
        if cause:
            context["cause"] = str(cause)
        super().__init__(message, context=context if context else None)
        self.strategy = strategy
        self.cause = cause
