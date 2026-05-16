"""Anthropic Claude 聊天模型策略。"""

from typing import Iterator, Optional

from langchain_anthropic import ChatAnthropic
from pydantic import SecretStr

from src.ai_chat.config import settings
from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.factory import register_chat
from src.ai_chat.llm.models import ChatRequest, ChatResponse, ProviderConfig, extract_usage
from src.ai_chat.llm.providers.chat.base import ChatProvider

logger = get_logger(__name__)


@register_chat("claude", lambda: ProviderConfig(
    api_key=settings.get_key(settings.anthropic_api_key),
))
class ClaudeProvider(ChatProvider):
    """Anthropic Claude 提供商策略。

    通过 langchain-anthropic 包对接 Claude API。
    支持 Claude 3/4 系列模型。

    支持模型：claude-sonnet-4-20250514, claude-3-5-sonnet-20241022, claude-3-opus-20240229 …
    """

    SUPPORTED_MODELS = [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "claude-3-haiku-20240307",
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()
        logger.debug("ClaudeProvider 初始化完成，timeout=%ds", self._config.timeout)

    def _get_api_key(self) -> SecretStr:
        """获取 API 密钥，优先使用实例配置，回退到空字符串。"""
        if self._config.api_key:
            return self._config.api_key
        logger.warning("Claude API 密钥未配置，请求可能失败")
        return SecretStr("")

    def get_client(self, model_name: str) -> ChatAnthropic:
        """获取 Claude LangChain 客户端实例（非流式）。"""
        logger.debug("创建 Claude 客户端: model=%s", model_name)
        return ChatAnthropic(
            model_name=model_name,
            api_key=self._get_api_key(),
            timeout=self._config.timeout,
            stop=None,
        )

    def get_stream_client(self, model_name: str, *, temperature: float = 0.7, max_tokens: Optional[int] = None, stop: Optional[list[str]] = None) -> ChatAnthropic:
        """获取带流式配置的 Claude LangChain 客户端。"""
        resolved_max_tokens = max_tokens or 4096
        logger.debug("创建 Claude 流式客户端: model=%s, temperature=%.2f, max_tokens=%d",
                     model_name, temperature, resolved_max_tokens)
        return ChatAnthropic(
            model_name=model_name,
            api_key=self._get_api_key(),
            temperature=temperature,
            max_tokens_to_sample=resolved_max_tokens,
            timeout=self._config.timeout,
            stop=stop
        )

    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        """发起 Claude 聊天请求。

        将 Claude 返回的 content 规范化为字符串格式：
        - 字符串直接使用
        - 列表格式（多模态响应）拼接为字符串
        """
        logger.info("Claude 聊天请求: model=%s, 消息数=%d, temperature=%.2f",
                     model_name, len(request.messages), request.temperature)
        llm = ChatAnthropic(
            model_name=model_name,
            api_key=self._get_api_key(),
            temperature=request.temperature,
            max_tokens_to_sample=request.max_tokens or 4096,
            timeout=self._config.timeout,
            stop=None,
        )
        result = llm.invoke(request.messages)

        # 将 content 规范化为字符串（Claude 可能返回列表格式的多模态内容）
        content = result.content
        if isinstance(content, list):
            content = "".join(
                item if isinstance(item, str) else str(item.get("text", "")) for item in content
            )

        usage = extract_usage(result)
        logger.info("Claude 聊天响应: model=%s, 内容长度=%d, usage=%s",
                     model_name, len(content), usage)
        return ChatResponse(
            content=content,
            model=model_name,
            usage=usage,
        )

    def stream(self, request: ChatRequest, model_name: str, *, stop: Optional[list[str]] = None) -> Iterator[str]:
        """流式 Claude 聊天，逐 token 返回文本片段。"""
        logger.info("Claude 流式请求: model=%s, 消息数=%d", model_name, len(request.messages))
        llm = self.get_stream_client(model_name, temperature=request.temperature, max_tokens=request.max_tokens, stop=stop)
        token_count = 0
        for chunk in llm.stream(request.messages):
            if isinstance(chunk.content, str) and chunk.content:
                token_count += 1
                yield chunk.content
        logger.debug("Claude 流式完成: model=%s, 共 %d 个 chunk", model_name, token_count)
