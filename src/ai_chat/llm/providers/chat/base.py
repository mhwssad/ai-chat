"""聊天模型提供商策略接口。"""

from abc import abstractmethod
from typing import Iterator, Optional

from langchain_core.language_models import BaseChatModel

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.base import ModelProvider
from src.ai_chat.llm.models import ChatRequest, ChatResponse

logger = get_logger(__name__)


class ChatProvider(ModelProvider):
    """聊天模型提供商策略。

    每个具体实现对应一个底层 API 提供商（OpenAI、Gemini、Claude …），
    内部维护该提供商支持的模型名称列表。
    子类必须实现 chat、get_client、get_stream_client、stream 四个抽象方法。
    """

    @property
    def provider_type(self) -> str:
        return "chat"

    @abstractmethod
    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        """使用指定的模型名称发起聊天请求。

        Args:
            request: 聊天请求对象，包含消息列表和生成参数
            model_name: 目标模型名称

        Returns:
            包含模型响应内容和元数据的 ChatResponse
        """

    @abstractmethod
    def get_client(self, model_name: str) -> BaseChatModel:
        """获取底层 LangChain 客户实例（供链/Agent 使用）。

        Args:
            model_name: 目标模型名称

        Returns:
            配置好的 BaseChatModel 实例
        """

    @abstractmethod
    def get_stream_client(self, model_name: str, *, temperature: float = 0.7, max_tokens: Optional[int] = None, stop: Optional[list[str]] = None) -> BaseChatModel:
        """获取带流式配置的 LangChain 客户实例。

        Args:
            model_name: 目标模型名称
            temperature: 采样温度，范围 0.0~2.0
            max_tokens: 最大生成 token 数
            stop: 停止词列表

        Returns:
            启用流式输出的 BaseChatModel 实例
        """

    @abstractmethod
    def stream(self, request: ChatRequest, model_name: str, *, stop: Optional[list[str]] = None) -> Iterator[str]:
        """流式聊天，逐 token 返回文本片段。

        Args:
            request: 聊天请求对象
            model_name: 目标模型名称
            stop: 可选的停止词列表

        Yields:
            str: 逐个 token 的文本片段
        """
