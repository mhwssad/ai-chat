"""Qwen 聊天模型策略。"""

from typing import Iterator, Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.ai_chat.config import settings
from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.factory import register_chat
from src.ai_chat.llm.models import ChatRequest, ChatResponse, ProviderConfig, extract_usage
from src.ai_chat.llm.providers.chat.base import ChatProvider

logger = get_logger(__name__)


@register_chat("qwen", lambda: ProviderConfig(
    api_key=settings.get_key(settings.qwen_api_key),
    base_url=settings.qwen_base_url,
))
class QwenProvider(ChatProvider):
    """Qwen 提供商策略。

    通过 langchain-openai 包以 OpenAI 兼容协议对接通义千问 API。
    通义千问 API 兼容 OpenAI 接口规范，因此复用 ChatOpenAI 客户端。

    支持模型：qwen-turbo
    """

    SUPPORTED_MODELS = [
        "qwen-turbo"
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()
        logger.debug("QwenProvider 初始化完成，base_url=%s", self._config.base_url)

    def get_client(self, model_name: str) -> BaseChatModel:
        """获取 Qwen LangChain 客户端实例（非流式，基于 OpenAI 兼容协议）。"""
        logger.debug("创建 Qwen 客户端: model=%s", model_name)
        return ChatOpenAI(
            model=model_name,
            api_key=self._config.api_key,
            base_url=self._config.base_url,
        )

    def get_stream_client(self, model_name: str, *, temperature: float = 0.7, max_tokens: Optional[int] = None, stop: Optional[list[str]] = None) -> BaseChatModel:
        """获取带流式配置的 Qwen LangChain 客户端。"""
        logger.debug("创建 Qwen 流式客户端: model=%s, temperature=%.2f, max_tokens=%s",
                     model_name, temperature, max_tokens)
        return ChatOpenAI(
            model=model_name,
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            streaming=True,
        )

    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        """发起 Qwen 聊天请求。"""
        logger.info("Qwen 聊天请求: model=%s, 消息数=%d, temperature=%.2f",
                     model_name, len(request.messages), request.temperature)
        llm = ChatOpenAI(
            model=model_name,
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            temperature=request.temperature,
            max_completion_tokens=request.max_tokens,
        )
        result = llm.invoke(request.messages)

        # 将 content 规范化为字符串
        content = result.content
        if isinstance(content, list):
            content = "".join(
                item if isinstance(item, str) else str(item.get("text", "")) for item in content
            )

        logger.info("Qwen 聊天响应: model=%s, 内容长度=%d", model_name, len(content))
        return ChatResponse(
            content=content,
            model=model_name,
            usage=extract_usage(result),
        )

    def stream(self, request: ChatRequest, model_name: str, *, stop: Optional[list[str]] = None) -> Iterator[str]:
        """流式 Qwen 聊天，逐 token 返回文本片段。"""
        logger.info("Qwen 流式请求: model=%s, 消息数=%d", model_name, len(request.messages))
        llm = self.get_stream_client(model_name, temperature=request.temperature, max_tokens=request.max_tokens, stop=stop)
        token_count = 0
        for chunk in llm.stream(request.messages):
            if isinstance(chunk.content, str) and chunk.content:
                token_count += 1
                yield chunk.content
        logger.debug("Qwen 流式完成: model=%s, 共 %d 个 chunk", model_name, token_count)
