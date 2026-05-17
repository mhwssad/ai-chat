"""Anthropic Claude 聊天模型策略。"""

from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr

from src.ai_chat.config import settings
from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.factory import register_chat
from src.ai_chat.llm.models import ProviderConfig
from src.ai_chat.llm.providers.chat.base import ChatProvider

logger = get_logger(__name__)


@register_chat(
    "claude",
    lambda: ProviderConfig(
        api_key=settings.get_key(settings.anthropic_api_key),
    ),
)
class ClaudeProvider(ChatProvider):
    """Anthropic Claude 提供商策略。"""

    SUPPORTED_MODELS = [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "claude-3-haiku-20240307",
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()

    def _get_api_key(self) -> SecretStr:
        """获取 API 密钥，优先使用实例配置，回退到空字符串。"""
        if self._config.api_key:
            return self._config.api_key
        logger.warning("Claude API 密钥未配置，请求可能失败")
        return SecretStr("")

    def _build_client(self, model_name: str, **kwargs) -> BaseChatModel:
        """构建 Claude LangChain 客户端。Claude 使用 model_name 参数名且 max_tokens 默认 4096。"""
        return ChatAnthropic(
            model_name=model_name,
            api_key=self._get_api_key(),
            temperature=kwargs.get("temperature"),
            max_tokens_to_sample=kwargs.get("max_tokens") or 4096,
            stop=kwargs.get("stop"),
            timeout=self._config.timeout,
        )
