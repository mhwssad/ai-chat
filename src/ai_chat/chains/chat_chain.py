"""常用调用链 — 基于 prompts registry 的即用型链。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Optional

from langchain_core.messages import BaseMessage

from src.ai_chat.chains.base import (
    ChainConfig,
    PromptContext,
    _BasePromptChain,
    _merge_context,
)
from src.ai_chat.prompts import render_messages


class ChatChain(_BasePromptChain):
    """简单对话链。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        prompt_key: str = "chain.chat",
        prompt_context: Optional[PromptContext] = None,
        config: Optional[ChainConfig] = None,
    ) -> None:
        super().__init__(model_name, prompt_key, prompt_context, config)

    def _build_messages(
        self,
        message: str,
        history: Optional[list[BaseMessage]] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> list[BaseMessage]:
        context = self._build_context(prompt_context, message=message)
        prompt_messages = render_messages(self._prompt_key, **context)
        return list(prompt_messages[:-1]) + list(history or []) + [prompt_messages[-1]]

    def invoke(
        self,
        message: str,
        history: Optional[list[BaseMessage]] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> str:
        return self._invoke_messages(self._build_messages(message, history, prompt_context))

    def stream(
        self,
        message: str,
        history: Optional[list[BaseMessage]] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> Iterator[str]:
        yield from self._stream_messages(self._build_messages(message, history, prompt_context))

    async def ainvoke(
        self,
        message: str,
        history: Optional[list[BaseMessage]] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> str:
        return await self._ainvoke_messages(self._build_messages(message, history, prompt_context))

    async def astream(
        self,
        message: str,
        history: Optional[list[BaseMessage]] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> AsyncIterator[str]:
        async for chunk in self._astream_messages(self._build_messages(message, history, prompt_context)):
            yield chunk


class SummarizeChain(_BasePromptChain):
    """文本摘要链。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        prompt_key: str = "chain.summarize",
        prompt_context: Optional[PromptContext] = None,
        config: Optional[ChainConfig] = None,
    ) -> None:
        defaults = {"language": "中文", "instruction": "请简洁地总结以下内容，保留关键信息："}
        merged_defaults = _merge_context(defaults, prompt_context, {})
        super().__init__(model_name, prompt_key, merged_defaults, config)

    def _build_messages(
        self,
        text: str,
        instruction: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> list[BaseMessage]:
        final: PromptContext = {"text": text}
        if instruction is not None:
            final["instruction"] = instruction
        context = self._build_context(prompt_context, **final)
        return render_messages(self._prompt_key, **context)

    def invoke(
        self,
        text: str,
        instruction: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> str:
        return self._invoke_messages(self._build_messages(text, instruction, prompt_context))

    def stream(
        self,
        text: str,
        instruction: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> Iterator[str]:
        yield from self._stream_messages(self._build_messages(text, instruction, prompt_context))

    async def ainvoke(
        self,
        text: str,
        instruction: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> str:
        return await self._ainvoke_messages(self._build_messages(text, instruction, prompt_context))

    async def astream(
        self,
        text: str,
        instruction: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> AsyncIterator[str]:
        async for chunk in self._astream_messages(self._build_messages(text, instruction, prompt_context)):
            yield chunk


class TranslateChain(_BasePromptChain):
    """翻译链。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        prompt_key: str = "chain.translate",
        prompt_context: Optional[PromptContext] = None,
        config: Optional[ChainConfig] = None,
    ) -> None:
        defaults = {"target": "中文"}
        merged_defaults = _merge_context(defaults, prompt_context, {})
        super().__init__(model_name, prompt_key, merged_defaults, config)

    def _build_messages(
        self,
        text: str,
        target: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> list[BaseMessage]:
        final: PromptContext = {"text": text}
        if target is not None:
            final["target"] = target
        context = self._build_context(prompt_context, **final)
        return render_messages(self._prompt_key, **context)

    def invoke(
        self,
        text: str,
        target: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> str:
        return self._invoke_messages(self._build_messages(text, target, prompt_context))

    def stream(
        self,
        text: str,
        target: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> Iterator[str]:
        yield from self._stream_messages(self._build_messages(text, target, prompt_context))

    async def ainvoke(
        self,
        text: str,
        target: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> str:
        return await self._ainvoke_messages(self._build_messages(text, target, prompt_context))

    async def astream(
        self,
        text: str,
        target: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> AsyncIterator[str]:
        async for chunk in self._astream_messages(self._build_messages(text, target, prompt_context)):
            yield chunk


class ExtractionChain(_BasePromptChain):
    """结构化信息抽取链。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        prompt_key: str = "chain.extraction",
        prompt_context: Optional[PromptContext] = None,
        config: Optional[ChainConfig] = None,
    ) -> None:
        super().__init__(model_name, prompt_key, prompt_context, config)

    def _build_messages(
        self,
        text: str,
        fields: list[str],
        prompt_context: Optional[PromptContext] = None,
    ) -> list[BaseMessage]:
        context = self._build_context(
            prompt_context,
            text=text,
            fields=fields,
            fields_desc="、".join(fields),
        )
        return render_messages(self._prompt_key, **context)

    def invoke(
        self,
        text: str,
        fields: list[str],
        prompt_context: Optional[PromptContext] = None,
    ) -> str:
        return self._invoke_messages(self._build_messages(text, fields, prompt_context))

    def stream(
        self,
        text: str,
        fields: list[str],
        prompt_context: Optional[PromptContext] = None,
    ) -> Iterator[str]:
        yield from self._stream_messages(self._build_messages(text, fields, prompt_context))

    async def ainvoke(
        self,
        text: str,
        fields: list[str],
        prompt_context: Optional[PromptContext] = None,
    ) -> str:
        return await self._ainvoke_messages(self._build_messages(text, fields, prompt_context))

    async def astream(
        self,
        text: str,
        fields: list[str],
        prompt_context: Optional[PromptContext] = None,
    ) -> AsyncIterator[str]:
        async for chunk in self._astream_messages(self._build_messages(text, fields, prompt_context)):
            yield chunk


class RefineChain(_BasePromptChain):
    """文本优化链。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        prompt_key: str = "chain.refine",
        prompt_context: Optional[PromptContext] = None,
        config: Optional[ChainConfig] = None,
    ) -> None:
        defaults = {"language": "中文"}
        merged_defaults = _merge_context(defaults, prompt_context, {})
        super().__init__(model_name, prompt_key, merged_defaults, config)

    def _build_messages(
        self,
        instruction: str,
        text: str,
        prompt_context: Optional[PromptContext] = None,
    ) -> list[BaseMessage]:
        context = self._build_context(prompt_context, instruction=instruction, text=text)
        return render_messages(self._prompt_key, **context)

    def invoke(
        self,
        instruction: str,
        text: str,
        prompt_context: Optional[PromptContext] = None,
    ) -> str:
        return self._invoke_messages(self._build_messages(instruction, text, prompt_context))

    def stream(
        self,
        instruction: str,
        text: str,
        prompt_context: Optional[PromptContext] = None,
    ) -> Iterator[str]:
        yield from self._stream_messages(self._build_messages(instruction, text, prompt_context))

    async def ainvoke(
        self,
        instruction: str,
        text: str,
        prompt_context: Optional[PromptContext] = None,
    ) -> str:
        return await self._ainvoke_messages(self._build_messages(instruction, text, prompt_context))

    async def astream(
        self,
        instruction: str,
        text: str,
        prompt_context: Optional[PromptContext] = None,
    ) -> AsyncIterator[str]:
        async for chunk in self._astream_messages(self._build_messages(instruction, text, prompt_context)):
            yield chunk
