"""代码审查链 — 审查代码质量并生成报告。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Optional

from src.ai_chat.chains.base import (
    ChainConfig,
    PromptContext,
    _BasePromptChain,
    _merge_context,
)
from src.ai_chat.prompts import render_messages


class CodeReviewChain(_BasePromptChain):
    """代码审查链 — 检查代码质量、安全性和最佳实践。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        prompt_key: str = "chain.code_review",
        prompt_context: Optional[PromptContext] = None,
        config: Optional[ChainConfig] = None,
    ) -> None:
        defaults = {"language": "中文"}
        merged_defaults = _merge_context(defaults, prompt_context, {})
        super().__init__(model_name, prompt_key, merged_defaults, config)

    def _build_messages(
        self,
        code: str,
        language: str = "",
        focus: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> list:
        final: PromptContext = {"code": code}
        if language:
            final["language"] = language
        if focus:
            final["focus"] = focus
        context = self._build_context(prompt_context, **final)
        return render_messages(self._prompt_key, **context)

    def invoke(
        self,
        code: str,
        language: str = "",
        focus: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> str:
        return self._invoke_messages(self._build_messages(code, language, focus, prompt_context))

    def stream(
        self,
        code: str,
        language: str = "",
        focus: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> Iterator[str]:
        yield from self._stream_messages(self._build_messages(code, language, focus, prompt_context))

    async def ainvoke(
        self,
        code: str,
        language: str = "",
        focus: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> str:
        return await self._ainvoke_messages(self._build_messages(code, language, focus, prompt_context))

    async def astream(
        self,
        code: str,
        language: str = "",
        focus: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> AsyncIterator[str]:
        async for chunk in self._astream_messages(self._build_messages(code, language, focus, prompt_context)):
            yield chunk
