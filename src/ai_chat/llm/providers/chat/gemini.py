"""Google Gemini 聊天模型策略。"""

from typing import Iterator, Optional

from langchain_google_genai import ChatGoogleGenerativeAI

from src.ai_chat.config import settings
from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.factory import register_chat
from src.ai_chat.llm.models import ChatRequest, ChatResponse, ProviderConfig, extract_usage
from src.ai_chat.llm.providers.chat.base import ChatProvider

logger = get_logger(__name__)


@register_chat("gemini", lambda: ProviderConfig(
    api_key=settings.get_key(settings.google_api_key),
))
class GeminiProvider(ChatProvider):
    """Google Gemini 提供商策略。

    通过 langchain-google-genai 包对接 Google AI API。
    支持 Gemini 1.5/2.0 系列模型。

    支持模型：gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash …
    """

    SUPPORTED_MODELS = [
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()
        logger.debug("GeminiProvider 初始化完成")

    def get_client(self, model_name: str) -> ChatGoogleGenerativeAI:
        """获取 Gemini LangChain 客户端实例（非流式）。"""
        logger.debug("创建 Gemini 客户端: model=%s", model_name)
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self._config.api_key,
        )

    def get_stream_client(self, model_name: str, *, temperature: float = 0.7, max_tokens: Optional[int] = None, stop: Optional[list[str]] = None) -> ChatGoogleGenerativeAI:
        """获取带流式配置的 Gemini LangChain 客户端。"""
        logger.debug("创建 Gemini 流式客户端: model=%s, temperature=%.2f, max_tokens=%s",
                     model_name, temperature, max_tokens)
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self._config.api_key,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        """发起 Gemini 聊天请求。

        将 Gemini 返回的 content 规范化为字符串格式。
        """
        logger.info("Gemini 聊天请求: model=%s, 消息数=%d, temperature=%.2f",
                     model_name, len(request.messages), request.temperature)
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self._config.api_key,
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
        )
        result = llm.invoke(request.messages)

        # 将 content 规范化为字符串（Gemini 可能返回列表格式的多模态内容）
        content = result.content
        if isinstance(content, list):
            content = "".join(
                item if isinstance(item, str) else str(item.get("text", "")) for item in content
            )

        usage = extract_usage(result)
        logger.info("Gemini 聊天响应: model=%s, 内容长度=%d, usage=%s",
                     model_name, len(content), usage)
        return ChatResponse(
            content=content,
            model=model_name,
            usage=usage,
        )

    def stream(self, request: ChatRequest, model_name: str, *, stop: Optional[list[str]] = None) -> Iterator[str]:
        """流式 Gemini 聊天，逐 token 返回文本片段。"""
        logger.info("Gemini 流式请求: model=%s, 消息数=%d", model_name, len(request.messages))
        llm = self.get_stream_client(model_name, temperature=request.temperature, max_tokens=request.max_tokens, stop=stop)
        token_count = 0
        for chunk in llm.stream(request.messages):
            if isinstance(chunk.content, str) and chunk.content:
                token_count += 1
                yield chunk.content
        logger.debug("Gemini 流式完成: model=%s, 共 %d 个 chunk", model_name, token_count)
