"""OpenAI 聊天模型策略。"""

from typing import Iterator, Optional

from langchain_openai import ChatOpenAI

from src.ai_chat.config import settings
from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.factory import register_chat
from src.ai_chat.llm.models import ChatRequest, ChatResponse, ProviderConfig, extract_usage
from src.ai_chat.llm.providers.chat.base import ChatProvider

logger = get_logger(__name__)


@register_chat("openai", lambda: ProviderConfig(
    api_key=settings.get_key(settings.openai_api_key),
    base_url=settings.openai_base_url or None,
))
class OpenAIProvider(ChatProvider):
    """OpenAI 提供商策略。

    通过 langchain-openai 包对接 OpenAI API，支持自定义 base_url 以兼容
    其他 OpenAI 兼容的 API 服务（如 Azure OpenAI、vLLM 等）。

    支持模型：gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-4, gpt-3.5-turbo, o1, o1-mini …
    """

    SUPPORTED_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "o1",
        "o1-mini",
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()
        logger.debug("OpenAIProvider 初始化完成，base_url=%s", self._config.base_url or "<默认>")

    def get_client(self, model_name: str) -> ChatOpenAI:
        """获取 OpenAI LangChain 客户端实例（非流式）。"""
        logger.debug("创建 OpenAI 客户端: model=%s", model_name)
        return ChatOpenAI(
            model=model_name,
            api_key=self._config.api_key,
            base_url=self._config.base_url,
        )

    def get_stream_client(self, model_name: str, *, temperature: float = 0.7, max_tokens: Optional[int] = None, stop: Optional[list[str]] = None) -> ChatOpenAI:
        """获取带流式配置的 OpenAI LangChain 客户端。"""
        logger.debug("创建 OpenAI 流式客户端: model=%s, temperature=%.2f, max_tokens=%s",
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
        """发起 OpenAI 聊天请求。

        将 OpenAI 返回的 content 规范化为字符串格式。
        """
        logger.info("OpenAI 聊天请求: model=%s, 消息数=%d, temperature=%.2f",
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

        logger.info("OpenAI 聊天响应: model=%s, 内容长度=%d", model_name, len(content))
        return ChatResponse(
            content=content,
            model=model_name,
            usage=extract_usage(result),
        )

    def stream(self, request: ChatRequest, model_name: str, *, stop: Optional[list[str]] = None) -> Iterator[str]:
        """流式 OpenAI 聊天，逐 token 返回文本片段。"""
        logger.info("OpenAI 流式请求: model=%s, 消息数=%d", model_name, len(request.messages))
        llm = self.get_stream_client(model_name, temperature=request.temperature, max_tokens=request.max_tokens, stop=stop)
        token_count = 0
        for chunk in llm.stream(request.messages):
            if isinstance(chunk.content, str) and chunk.content:
                token_count += 1
                yield chunk.content
        logger.debug("OpenAI 流式完成: model=%s, 共 %d 个 chunk", model_name, token_count)
