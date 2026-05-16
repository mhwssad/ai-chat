"""数据类、异常与工具函数定义。"""

from dataclasses import dataclass, field
from typing import Optional, Union

from pydantic import SecretStr

from langchain_core.messages import AIMessage


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


def mask_key(key: Union[SecretStr, str, None]) -> str:
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

    messages: list = field(default_factory=list)
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    extra: dict = field(default_factory=dict)


@dataclass
class ChatResponse:
    """聊天响应。"""

    content: str
    model: str
    usage: Optional[dict] = None


def extract_usage(result: AIMessage) -> Optional[dict]:
    """从 LangChain AIMessage 响应中提取 token 使用量。

    兼容不同提供商的 metadata 格式：
    - OpenAI: ``result.response_metadata["token_usage"]``
    - Claude: ``result.response_metadata["usage"]``
    - 通用:   ``result.usage_metadata`` (langchain-core >= 0.2)
    """
    meta = result.response_metadata or {}

    if "token_usage" in meta:
        return meta["token_usage"]

    if "usage" in meta:
        return meta["usage"]

    if hasattr(result, "usage_metadata") and result.usage_metadata:
        um = result.usage_metadata
        return {
            "input_tokens": getattr(um, "input_tokens", None),
            "output_tokens": getattr(um, "output_tokens", None),
            "total_tokens": getattr(um, "total_tokens", None),
        }

    return None
