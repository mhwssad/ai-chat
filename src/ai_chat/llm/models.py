"""数据类、异常与工具函数定义。"""

from dataclasses import dataclass, field
from typing import Optional, Union

from pydantic import SecretStr

from langchain_core.messages import AIMessage

from src.ai_chat.config.base_exception import BaseExceptions
from src.ai_chat.config.logging_setup import get_logger

logger = get_logger(__name__)


# ======================================================================
# 异常
# ======================================================================


class ModelNotSupportedException(Exception):
    """请求的模型名称未被任何已注册的提供商策略支持。"""

    def __init__(self, model_name: str, supported: list[str]) -> None:
        self.model_name = model_name
        self.supported_models = supported
        detail = f"模型 '{model_name}' 不受支持。已注册模型：{supported}"
        super().__init__(detail)


class LLMException(BaseExceptions):
    """LLM 调用基础异常。"""


class LLMRetryExhaustedError(LLMException):
    """LLM 重试次数耗尽。"""


class LLMCircuitOpenError(LLMException):
    """熔断器已开启，拒绝请求。"""


# ======================================================================
# 提供商实例配置
# ======================================================================


@dataclass
class ProviderConfig:
    """提供商实例级配置。未设置的字段回退到全局 settings。

    Attributes:
        base_url: API 基础地址，None 时使用 SDK 默认值
        api_key: API 密钥，以 SecretStr 包装防止意外泄露
        timeout: 请求超时时间（秒）
    """

    base_url: Optional[str] = None
    api_key: Optional[SecretStr] = None
    timeout: int = 60


def mask_key(key: Union[SecretStr, str, None]) -> str:
    """API Key 脱敏，仅显示前后 4 位。如 ``sk-a****9xyz``。

    用于日志输出和调试时安全地展示密钥信息，避免完整密钥泄露。
    """
    if key is None:
        return "<none>"
    raw = key.get_secret_value() if isinstance(key, SecretStr) else str(key)
    if len(raw) <= 8:
        return "****"
    return f"{raw[:4]}****{raw[-4:]}"


# ======================================================================
# 请求 / 响应
# ======================================================================


@dataclass
class ChatRequest:
    """聊天请求。

    Attributes:
        messages: LangChain 消息列表（SystemMessage / HumanMessage / AIMessage）
        temperature: 采样温度，越高输出越随机，范围 0.0~2.0
        max_tokens: 单次响应最大 token 数，None 时使用模型默认值
        extra: 供应商特有的额外参数，透传给底层 API
    """

    messages: list = field(default_factory=list)
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    extra: dict = field(default_factory=dict)
    skip_cache: bool = False


@dataclass
class ChatResponse:
    """聊天响应。

    Attributes:
        content: 模型生成的文本内容（已规范化为字符串）
        model: 实际使用的模型名称
        usage: token 使用量统计，格式因供应商而异，None 表示不可用
    """

    content: str
    model: str
    usage: Optional[dict] = None


def extract_usage(result: AIMessage) -> Optional[dict]:
    """从 LangChain AIMessage 响应中提取 token 使用量。

    兼容不同提供商的 metadata 格式：
    - OpenAI: ``result.response_metadata["token_usage"]``
    - Claude: ``result.response_metadata["usage"]``
    - 通用:   ``result.usage_metadata`` (langchain-core >= 0.2)

    Args:
        result: LangChain 的 AIMessage 响应对象

    Returns:
        包含 token 使用量的字典，无法提取时返回 None
    """
    meta = result.response_metadata or {}

    # OpenAI 风格：token_usage 字段
    if "token_usage" in meta:
        logger.debug("从 response_metadata['token_usage'] 提取 token 使用量")
        return meta["token_usage"]

    # Claude 风格：usage 字段
    if "usage" in meta:
        logger.debug("从 response_metadata['usage'] 提取 token 使用量")
        return meta["usage"]

    # langchain-core >= 0.2 通用字段
    if hasattr(result, "usage_metadata") and result.usage_metadata:
        um = result.usage_metadata
        logger.debug("从 usage_metadata 提取 token 使用量")
        return {
            "input_tokens": getattr(um, "input_tokens", None),
            "output_tokens": getattr(um, "output_tokens", None),
            "total_tokens": getattr(um, "total_tokens", None),
        }

    logger.warning(
        "无法从 AIMessage 中提取 token 使用量，response_metadata keys: %s",
        list(meta.keys()),
    )
    return None
