"""项目统一异常。"""

from src.ai.exception.base_exception import BaseExceptions
from src.ai.exception.llm_exception import (
    LLMCircuitOpenError,
    LLMException,
    LLMRetryExhaustedError,
    ModelNotSupportedException,
)

__all__ = [
    "BaseExceptions",
    "LLMCircuitOpenError",
    "LLMException",
    "LLMRetryExhaustedError",
    "ModelNotSupportedException",
]

