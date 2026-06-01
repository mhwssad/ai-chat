"""Token 计数工具 — API 优先使用量提取 + tiktoken 本地精确计数。

核心策略：优先使用 LLM API 返回的 token 使用量，仅在 API 未提供时回退到本地 tiktoken 估算。

使用方式::

    from src.ai.utils.token_utils import token_counter, TokenUsage

    # 从 AIMessage 获取 usage（API 优先，本地回退）
    usage = token_counter.from_response(result)

    # 本地计数
    n = token_counter.count_text_tokens("你好世界")
    total = token_counter.estimate_messages_tokens(messages)
"""

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import BaseMessage, AIMessage

from src.ai.config.logging_setup import get_logger

logger = get_logger(__name__)


# ======================================================================
# 数据类
# ======================================================================


@dataclass
class TokenUsage:
    """统一的 token 使用量数据。

    Attributes:
        prompt_tokens: 输入 token 数（发送给 LLM 的上下文）
        completion_tokens: 输出 token 数（LLM 生成的回复）
        total_tokens: 总 token 数
        source: 数据来源 — "api"（LLM 返回）、"local"（tiktoken 估算）、"unknown"
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    source: str = "unknown"


class TokenCounter:
    """Token 计数器 — 封装 tiktoken 本地计数与 API 使用量提取。

    职责：
    1. tiktoken 本地计数（文本 / 单条消息 / 消息列表）
    2. 从 AIMessage 提取各供应商的 API 使用量
    3. 标准化各供应商 usage 字典为统一 TokenUsage
    4. API 优先 + 本地回退的综合查询

    Args:
        chars_per_token: 字符级回退的估算比率，默认 3.5 字符/token
    """

    def __init__(self, chars_per_token: float = 3.5) -> None:
        self._encoder: Any = None
        self._chars_per_token = chars_per_token

    # ------------------------------------------------------------------
    # tiktoken 本地计数
    # ------------------------------------------------------------------

    def _get_encoder(self):
        """获取 tiktoken 编码器实例（cl100k_base，GPT-4/GPT-4o 同款）。

        延迟导入 tiktoken 以避免模块加载时的网络请求（首次调用时下载词表）。
        """
        if self._encoder is not None:
            return self._encoder
        try:
            import tiktoken

            self._encoder = tiktoken.get_encoding("cl100k_base")
            logger.debug("tiktoken cl100k_base 编码器加载成功")
        except ImportError:
            logger.warning("tiktoken 未安装，回退到字符级 token 估算（精度约 ±30%）")
            self._encoder = False
        except Exception as e:
            logger.warning("tiktoken 加载失败: %s，回退到字符级估算", e)
            self._encoder = False
        return self._encoder if self._encoder is not False else None

    def count_text_tokens(self, text: str) -> int:
        """精确计算文本的 token 数量。

        使用 tiktoken cl100k_base 编码器计数。
        tiktoken 不可用时回退到字符级估算（约 3.5 字符/token）。
        """
        encoder = self._get_encoder()
        if encoder is not None:
            return len(encoder.encode(text))
        return max(1, int(len(text) / self._chars_per_token))

    @staticmethod
    def _extract_text_content(content) -> str:
        """从消息 content 中提取纯文本。"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                item if isinstance(item, str) else str(item.get("text", ""))
                for item in content
            )
        return str(content)

    def estimate_message_tokens(self, message: BaseMessage) -> int:
        """估算单条 LangChain 消息的 token 数。

        对 content 调用 tiktoken 计数，加上 4 token 的消息元数据开销。
        """
        text = self._extract_text_content(message.content)
        return self.count_text_tokens(text) + 4

    def estimate_messages_tokens(self, messages: list[BaseMessage]) -> int:
        """估算消息列表的总 token 数。"""
        return sum(self.estimate_message_tokens(msg) for msg in messages)

    # ------------------------------------------------------------------
    # API 使用量提取与标准化
    # ------------------------------------------------------------------

    @staticmethod
    def extract_usage(result: AIMessage) -> dict | None:
        """从 LangChain AIMessage 响应中提取 token 使用量。

        兼容不同提供商的 metadata 格式：
        - OpenAI: ``result.response_metadata["token_usage"]``
        - Claude: ``result.response_metadata["usage"]``
        - 通用:   ``result.usage_metadata`` (langchain-core >= 0.2)

        Args:
            result: LangChain 的 AIMessage 响应对象

        Returns:
            包含 token 使用量的字典，无法提取时返回 None
        """
        meta = result.response_metadata or {}

        if "token_usage" in meta:
            logger.debug("从 response_metadata['token_usage'] 提取 token 使用量")
            return meta["token_usage"]

        if "usage" in meta:
            logger.debug("从 response_metadata['usage'] 提取 token 使用量")
            return meta["usage"]

        if hasattr(result, "usage_metadata") and result.usage_metadata:
            um = result.usage_metadata
            logger.debug("从 usage_metadata 提取 token 使用量")
            return {
                "input_tokens": getattr(um, "input_tokens", None),
                "output_tokens": getattr(um, "output_tokens", None),
                "total_tokens": getattr(um, "total_tokens", None),
            }

        logger.debug(
            "无法从 AIMessage 中提取 token 使用量，response_metadata keys: %s",
            list(meta.keys()),
        )
        return None

    @staticmethod
    def normalize_usage(usage: dict) -> TokenUsage:
        """将各供应商的 usage 字典统一为 TokenUsage。

        支持的格式：
        - OpenAI: ``{'prompt_tokens': N, 'completion_tokens': M, 'total_tokens': T}``
        - Claude/Gemini: ``{'input_tokens': N, 'output_tokens': M}``
        """
        prompt = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
        completion = usage.get("completion_tokens") or usage.get("output_tokens") or 0
        total = usage.get("total_tokens")
        if total is None:
            total = prompt + completion
        return TokenUsage(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
            source="api",
        )

    # ------------------------------------------------------------------
    # 核心入口：API 优先 + 本地回退
    # ------------------------------------------------------------------

    def from_response(self, result: AIMessage) -> TokenUsage:
        """从 AIMessage 获取 token 使用量 — API 优先，本地回退。

        优先级:
        1. 从 response_metadata / usage_metadata 提取 API 返回的使用量
        2. 提取失败时，用 tiktoken 估算 AI 回复的 token 数（仅 completion 部分）
        """
        usage_dict = self.extract_usage(result)
        if usage_dict is not None:
            return self.normalize_usage(usage_dict)

        completion_tokens = self.estimate_message_tokens(result)
        logger.debug(
            "API 未返回 token 使用量，使用 tiktoken 估算: completion=%d",
            completion_tokens,
        )
        return TokenUsage(
            prompt_tokens=0,
            completion_tokens=completion_tokens,
            total_tokens=completion_tokens,
            source="local",
        )

    def from_messages(
        self,
        messages: list[BaseMessage],
        *,
        result: AIMessage | None = None,
    ) -> TokenUsage:
        """获取消息列表的 token 使用量。

        有 result 时优先用 API 返回的 usage（from_response），
        无 result 时用 tiktoken 累加所有消息。
        """
        if result is not None:
            api_usage = self.from_response(result)
            if api_usage.source == "api":
                if api_usage.prompt_tokens == 0:
                    api_usage.prompt_tokens = self.estimate_messages_tokens(messages)
                    api_usage.total_tokens = (
                        api_usage.prompt_tokens + api_usage.completion_tokens
                    )
                return api_usage

        total = self.estimate_messages_tokens(messages)
        logger.debug(
            "使用 tiktoken 估算消息列表: total=%d, 消息数=%d", total, len(messages)
        )
        return TokenUsage(
            prompt_tokens=total,
            completion_tokens=0,
            total_tokens=total,
            source="local",
        )


# ======================================================================
# 全局默认实例 + 向后兼容的模块级快捷函数
# ======================================================================

token_counter = TokenCounter()

count_text_tokens = token_counter.count_text_tokens
estimate_message_tokens = token_counter.estimate_message_tokens
estimate_messages_tokens = token_counter.estimate_messages_tokens
extract_usage = token_counter.extract_usage
normalize_usage = token_counter.normalize_usage
from_response = token_counter.from_response
from_messages = token_counter.from_messages
