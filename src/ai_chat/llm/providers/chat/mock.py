"""Mock 聊天模型策略 — 用于测试和开发环境，不发起真实 API 调用。"""

from typing import Iterator, Optional

from langchain_core.language_models import BaseChatModel

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.factory import register_chat
from src.ai_chat.llm.models import (
    ChatRequest,
    ChatResponse,
    ProviderConfig,
)
from src.ai_chat.llm.providers.chat.base import ChatProvider

logger = get_logger(__name__)


@register_chat(
    "mock",
    lambda: ProviderConfig(),
    requires_key=False,
)
class MockChatProvider(ChatProvider):
    """Mock 提供商策略 — 返回预设的固定响应，用于测试。

    支持模型：mock-default。
    可通过 MockChatProvider.set_default_response() 配置类级别默认响应，
    或通过实例的 set_response() 配置实例级别响应。

    用法::

        # 类级别：影响所有实例
        MockChatProvider.set_default_response("测试回复")

        # 实例级别：覆盖类默认
        provider = llm_factory.get_chat_provider("mock-default")
        provider.set_response("自定义回复")
    """

    SUPPORTED_MODELS = ["mock-default"]

    _default_response: str = "这是 Mock 提供商的默认响应。"

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()
        self._custom_response: Optional[str] = None
        logger.debug("MockChatProvider 初始化完成")

    @classmethod
    def set_default_response(cls, response: str) -> None:
        """设置类级别默认响应（影响所有 MockChatProvider 实例）。"""
        cls._default_response = response

    def set_response(self, response: str) -> None:
        """设置实例级别响应（覆盖类默认）。"""
        self._custom_response = response

    def _get_response_text(self) -> str:
        return self._custom_response or self._default_response

    def _build_client(self, model_name: str, **kwargs) -> BaseChatModel:
        """Mock 不需要真实客户端。"""
        return None  # type: ignore[return-value]

    def get_client(self, model_name: str) -> BaseChatModel:
        """Mock 不需要真实客户端，返回 None。"""
        return None  # type: ignore[return-value]

    def get_stream_client(
        self,
        model_name: str,
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[list[str]] = None,
    ) -> BaseChatModel:
        """Mock 不需要真实客户端，返回 None。"""
        return None  # type: ignore[return-value]

    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        """返回预设的固定响应。"""
        text = self._get_response_text()
        logger.info(
            "Mock 聊天请求: model=%s, 返回预设响应 (长度=%d)", model_name, len(text)
        )
        return ChatResponse(
            content=text,
            model=model_name,
            usage={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        )

    def stream(
        self, request: ChatRequest, model_name: str, *, stop: Optional[list[str]] = None
    ) -> Iterator[str]:
        """逐字符返回预设响应。"""
        text = self._get_response_text()
        logger.info("Mock 流式请求: model=%s", model_name)
        for char in text:
            yield char
