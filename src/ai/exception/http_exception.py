"""HTTP 相关异常。"""


from src.ai.exception.base_exception import BaseExceptions


class HttpError(BaseExceptions):
    """HTTP 请求失败异常。"""

    def __init__(
        self,
        message: str,
        *,
        url: str = "",
        method: str = "",
        status_code: int | None = None,
    ) -> None:
        self.url = url
        self.method = method
        self.status_code = status_code
        super().__init__(
            message,
            context={"url": url, "method": method, "status_code": status_code},
            error_code="HTTP_ERROR",
        )


class ConverterError(BaseExceptions):
    """实体转换失败异常。"""
