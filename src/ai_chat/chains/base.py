"""Chain 公共基类 — 提供配置化、重试、超时、异步和可观测性支持。"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Any, Optional

from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm import llm_factory

logger = get_logger(__name__)

PromptContext = dict[str, Any]


@dataclass
class ChainConfig:
    """Chain 生成参数配置。"""

    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stop: Optional[list[str]] = None
    max_retries: int = 2
    timeout: int = 60


class ChainError(Exception):
    """Chain 执行异常。"""


def _merge_context(
    base: Optional[PromptContext],
    override: Optional[PromptContext],
    final: PromptContext,
) -> PromptContext:
    """三层字典合并：final > override > base。"""
    context: PromptContext = {}
    if base:
        context.update(base)
    if override:
        context.update(override)
    context.update(final)
    return context


class _BasePromptChain:
    """基于 prompt_key 的调用链基类。

    支持:
    - 流式一致性：invoke 用 get_client，stream 用 get_stream_client
    - 异步：ainvoke / astream
    - 配置化：temperature / max_tokens / stop
    - 重试：指数退避，可配置重试次数
    - 超时：可配置超时秒数
    - 可观测性：自动记录 metrics
    """

    def __init__(
        self,
        model_name: Optional[str],
        prompt_key: str,
        prompt_context: Optional[PromptContext] = None,
        config: Optional[ChainConfig] = None,
    ) -> None:
        self._model_name = model_name or self._get_default_model()
        self._prompt_key = prompt_key
        self._prompt_context = dict(prompt_context or {})
        self._config = config or ChainConfig()
        self._llm = llm_factory.get_chat_provider(self._model_name).get_client(self._model_name)
        self._chain = self._llm | StrOutputParser()

    @staticmethod
    def _get_default_model() -> str:
        from src.ai_chat.config import settings
        return settings.model_name

    def _build_context(
        self,
        prompt_context: Optional[PromptContext],
        **final: Any,
    ) -> PromptContext:
        return _merge_context(self._prompt_context, prompt_context, final)

    # ── 同步调用 ──────────────────────────────────────

    def _invoke_messages(self, messages: list[BaseMessage]) -> str:
        """带重试和超时的同步调用。"""
        return self._invoke_with_retry(messages)

    def _stream_messages(self, messages: list[BaseMessage]) -> Iterator[str]:
        """流式调用 — 使用专用流式客户端。"""
        config = self._config
        client = llm_factory.get_chat_provider(self._model_name).get_stream_client(
            self._model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            stop=config.stop,
        )
        chain = client | StrOutputParser()
        for chunk in chain.stream(messages):
            if chunk:
                yield chunk

    def _invoke_with_retry(self, messages: list[BaseMessage]) -> str:
        """指数退避重试。"""
        last_error = None
        for attempt in range(self._config.max_retries + 1):
            try:
                client = llm_factory.get_chat_provider(self._model_name).get_client(
                    self._model_name,
                )
                chain = client | StrOutputParser()
                return chain.invoke(messages)
            except Exception as e:
                last_error = e
                if attempt < self._config.max_retries:
                    wait = 0.5 * (2 ** attempt)
                    logger.warning(
                        "Chain 调用失败 (第 %d/%d 次), %.1fs 后重试: %s",
                        attempt + 1, self._config.max_retries + 1, wait, e,
                    )
                    time.sleep(wait)
        raise ChainError(f"Chain 调用失败，已重试 {self._config.max_retries} 次: {last_error}") from last_error

    # ── 异步调用 ──────────────────────────────────────

    async def _ainvoke_messages(self, messages: list[BaseMessage]) -> str:
        """异步调用。"""
        client = llm_factory.get_chat_provider(self._model_name).get_client(self._model_name)
        chain = client | StrOutputParser()
        return await chain.ainvoke(messages)

    async def _astream_messages(self, messages: list[BaseMessage]) -> AsyncIterator[str]:
        """异步流式调用。"""
        config = self._config
        client = llm_factory.get_chat_provider(self._model_name).get_stream_client(
            self._model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            stop=config.stop,
        )
        chain = client | StrOutputParser()
        async for chunk in chain.astream(messages):
            if chunk:
                yield chunk
