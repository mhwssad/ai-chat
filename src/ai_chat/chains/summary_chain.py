"""对话摘要链 — 将对话消息压缩为摘要。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from src.ai_chat.chains.base import ChainConfig, ChainError, _BasePromptChain


class ConversationSummaryChain(_BasePromptChain):
    """将对话历史压缩为简洁摘要，保留关键事实和上下文。

    不使用 prompt_registry（硬编码 prompt 更适合内部摘要场景），
    但继承基类的重试、配置和客户端管理。
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        token_limit: int = 500,
        config: Optional[ChainConfig] = None,
    ) -> None:
        super().__init__(model_name, prompt_key="", config=config)
        self._token_limit = token_limit

    def _build_summary_messages(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """构建摘要请求消息。"""
        conversation_text = "\n".join(
            f"{msg.type}: {msg.content}" for msg in messages
        )
        return [
            SystemMessage(
                content=(
                    "你是一个对话摘要助手。请简洁地总结以下对话，"
                    "保留关键事实、决定和上下文信息。"
                    f"摘要控制在 {self._token_limit} token 以内。"
                )
            ),
            HumanMessage(content=conversation_text),
        ]

    def invoke(self, messages: list[BaseMessage]) -> Optional[str]:
        """对消息列表生成摘要。失败时返回 None。"""
        try:
            return self._invoke_messages(self._build_summary_messages(messages))
        except ChainError as e:
            from src.ai_chat.config.logging_setup import get_logger
            get_logger(__name__).warning("摘要生成失败: %s", e)
            return None

    def stream(self, messages: list[BaseMessage]) -> Iterator[str]:
        yield from self._stream_messages(self._build_summary_messages(messages))

    async def ainvoke(self, messages: list[BaseMessage]) -> Optional[str]:
        """异步生成摘要。"""
        try:
            return await self._ainvoke_messages(self._build_summary_messages(messages))
        except ChainError:
            return None

    async def astream(self, messages: list[BaseMessage]) -> AsyncIterator[str]:
        async for chunk in self._astream_messages(self._build_summary_messages(messages)):
            yield chunk
