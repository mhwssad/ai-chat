"""策略接口、数据类与异常定义（聊天模型 + 嵌入模型）。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from pydantic import SecretStr

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage


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


# ======================================================================
# 提供商实例配置
# ======================================================================

@dataclass
class ProviderConfig:
    """提供商实例级配置。未设置的字段回退到全局 settings。"""

    base_url: Optional[str] = None
    api_key: Optional[SecretStr] = None
    timeout: int = 60


def mask_key(key: SecretStr | str | None) -> str:
    """API Key 脱敏，仅显示前后 4 位。如 ``sk-a****9xyz``。"""
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
    """聊天请求。"""

    messages: list[BaseMessage]
    temperature: float = 0.7
    max_tokens: int | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class ChatResponse:
    """聊天响应。"""

    content: str
    model: str
    usage: dict | None = None


def extract_usage(result: AIMessage) -> dict | None:
    """从 LangChain AIMessage 响应中提取 token 使用量。

    兼容不同提供商的 metadata 格式：
    - OpenAI: ``result.response_metadata["token_usage"]``
    - Claude: ``result.response_metadata["usage"]``
    - 通用:   ``result.usage_metadata`` (langchain-core >= 0.2)
    """
    meta = result.response_metadata or {}

    # OpenAI / 通用格式: {"prompt_tokens", "completion_tokens", "total_tokens"}
    if "token_usage" in meta:
        return meta["token_usage"]

    # Claude 格式: {"input_tokens", "output_tokens"}
    if "usage" in meta:
        return meta["usage"]

    # langchain-core usage_metadata: UsageMetadata(input_tokens=..., output_tokens=..., total_tokens=...)
    if hasattr(result, "usage_metadata") and result.usage_metadata:
        um = result.usage_metadata
        return {
            "input_tokens": getattr(um, "input_tokens", None),
            "output_tokens": getattr(um, "output_tokens", None),
            "total_tokens": getattr(um, "total_tokens", None),
        }

    return None


# ======================================================================
# 策略接口
# ======================================================================

class ChatProvider(ABC):
    """聊天模型提供商策略。

    每个具体实现对应一个底层 API 提供商（OpenAI、Gemini、Claude …），
    内部维护该提供商支持的模型名称列表。
    """

    @abstractmethod
    def supports_model(self, model_name: str) -> bool:
        """判断该策略是否支持给定的模型名称。"""

    @abstractmethod
    def get_supported_models(self) -> list[str]:
        """返回该策略支持的所有模型名称列表。"""

    @abstractmethod
    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        """使用指定的模型名称发起聊天请求。"""

    @abstractmethod
    def get_client(self, model_name: str) -> BaseChatModel:
        """获取底层 LangChain 客户实例（供链/Agent 使用）。"""


# ======================================================================
# 嵌入模型 — 策略接口
# ======================================================================

class EmbeddingProvider(ABC):
    """嵌入模型提供商策略。

    与 ``ChatProvider`` 职责分离，专门处理文本向量化。
    每个具体实现对应一个底层嵌入 API（OpenAI Embeddings、本地模型 …）。
    """

    @abstractmethod
    def supports_model(self, model_name: str) -> bool:
        """判断该策略是否支持给定的嵌入模型名称。"""

    @abstractmethod
    def get_supported_models(self) -> list[str]:
        """返回该策略支持的所有嵌入模型名称列表。"""

    @abstractmethod
    def embed(self, text: str, model_name: str) -> list[float]:
        """使用指定的嵌入模型对单段文本进行向量化。"""

    @abstractmethod
    def embed_batch(self, texts: list[str], model_name: str) -> list[list[float]]:
        """批量嵌入多段文本。"""

