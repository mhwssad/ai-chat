"""Ollama 本地聊天模型策略。"""

from typing import Iterator, Optional

from langchain_ollama import ChatOllama

from src.ai_chat.config import settings
from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.factory import register_chat
from src.ai_chat.llm.models import ChatRequest, ChatResponse, ProviderConfig, extract_usage
from src.ai_chat.llm.providers.chat.base import ChatProvider

logger = get_logger(__name__)


@register_chat("ollama", lambda: ProviderConfig(
    base_url=settings.ollama_base_url,
), requires_key=False)
class OllamaProvider(ChatProvider):
    """Ollama 本地聊天提供商策略。

    通过 langchain-ollama 包对接本地 Ollama 服务。
    无需 API 密钥（requires_key=False），模型在本地运行。

    支持 Ollama 本地运行的所有模型，模型名称需与本地已拉取的模型一致。
    常见模型：qwen2.5, llama3.1, mistral, gemma2, deepseek-r1 …
    """

    SUPPORTED_MODELS = [
        "qwen2.5",
        "qwen2.5:7b",
        "qwen2.5:14b",
        "llama3.1",
        "llama3.1:8b",
        "llama3.1:70b",
        "mistral",
        "gemma2",
        "gemma2:9b",
        "deepseek-r1",
        "deepseek-r1:8b",
        "phi4",
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self._config = config or ProviderConfig()
        logger.debug("OllamaProvider 初始化完成，base_url=%s", self._config.base_url)

    def get_client(self, model_name: str) -> ChatOllama:
        """获取 Ollama LangChain 客户端实例（非流式）。"""
        logger.debug("创建 Ollama 客户端: model=%s", model_name)
        return ChatOllama(
            model=model_name,
            base_url=self._config.base_url,
        )

    def get_stream_client(self, model_name: str, *, temperature: float = 0.7, max_tokens: Optional[int] = None, stop: Optional[list[str]] = None) -> ChatOllama:
        """获取带流式配置的 Ollama LangChain 客户端。

        Ollama 使用 num_predict 参数控制最大生成 token 数。
        """
        logger.debug("创建 Ollama 流式客户端: model=%s, temperature=%.2f, max_tokens=%s",
                     model_name, temperature, max_tokens)
        return ChatOllama(
            model=model_name,
            base_url=self._config.base_url,
            temperature=temperature,
            num_predict=max_tokens,
        )

    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        """发起 Ollama 本地聊天请求。

        将 Ollama 返回的 content 规范化为字符串格式。
        """
        logger.info("Ollama 聊天请求: model=%s, 消息数=%d, temperature=%.2f",
                     model_name, len(request.messages), request.temperature)
        llm = ChatOllama(
            model=model_name,
            base_url=self._config.base_url,
            temperature=request.temperature,
            num_predict=request.max_tokens,
        )
        result = llm.invoke(request.messages)

        # 将 content 规范化为字符串
        content = result.content
        if isinstance(content, list):
            content = "".join(
                item if isinstance(item, str) else str(item.get("text", "")) for item in content
            )

        usage = extract_usage(result)
        logger.info("Ollama 聊天响应: model=%s, 内容长度=%d, usage=%s",
                     model_name, len(content), usage)
        return ChatResponse(
            content=content,
            model=model_name,
            usage=usage,
        )

    def stream(self, request: ChatRequest, model_name: str, *, stop: Optional[list[str]] = None) -> Iterator[str]:
        """流式 Ollama 聊天，逐 token 返回文本片段。"""
        logger.info("Ollama 流式请求: model=%s, 消息数=%d", model_name, len(request.messages))
        llm = self.get_stream_client(model_name, temperature=request.temperature, max_tokens=request.max_tokens, stop=stop)
        token_count = 0
        for chunk in llm.stream(request.messages):
            if isinstance(chunk.content, str) and chunk.content:
                token_count += 1
                yield chunk.content
        logger.debug("Ollama 流式完成: model=%s, 共 %d 个 chunk", model_name, token_count)
