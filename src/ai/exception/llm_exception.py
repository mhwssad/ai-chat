from src.ai.exception.base_exception import BaseExceptions


class ModelNotSupportedException(BaseExceptions):
    """请求的模型名称未被任何已注册的提供商策略支持。"""

    def __init__(self, model_name: str, supported: list[str]) -> None:
        self.model_name = model_name
        self.supported_models = supported
        detail = f"模型 '{model_name}' 不受支持。已注册模型：{supported}"
        super().__init__(
            detail,
            context={"model_name": model_name, "supported_models": supported},
            error_code="MODEL_NOT_SUPPORTED",
        )


class LLMException(BaseExceptions):
    """LLM 调用基础异常。"""


class LLMRetryExhaustedError(LLMException):
    """LLM 重试次数耗尽。"""


class LLMCircuitOpenError(LLMException):
    """熔断器已开启，拒绝请求。"""
