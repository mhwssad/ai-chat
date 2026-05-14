"""常用调用链 — 基于 prompts registry 的即用型链。"""

from __future__ import annotations

from typing import Any, Iterator, Optional

from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser

from src.ai_chat.llm import llm_factory
from src.ai_chat.prompts import render_messages


PromptContext = dict[str, Any]


def _merge_context(
    base: Optional[PromptContext],
    override: Optional[PromptContext],
    final: PromptContext,
) -> PromptContext:
    context: PromptContext = {}
    if base:
        context.update(base)
    if override:
        context.update(override)
    context.update(final)
    return context


class _BasePromptChain:
    """基于 prompt_key 的调用链基类。"""

    def __init__(
        self,
        model_name: Optional[str],
        prompt_key: str,
        prompt_context: Optional[PromptContext] = None,
    ) -> None:
        self._model_name = model_name or self._get_default_model()
        self._prompt_key = prompt_key
        self._prompt_context = dict(prompt_context or {})
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

    def _invoke_messages(self, messages: list[BaseMessage]) -> str:
        return self._chain.invoke(messages)

    def _stream_messages(self, messages: list[BaseMessage]) -> Iterator[str]:
        for chunk in self._chain.stream(messages):
            if chunk:
                yield chunk


class ChatChain(_BasePromptChain):
    """简单对话链。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        prompt_key: str = "chain.chat",
        prompt_context: Optional[PromptContext] = None,
    ) -> None:
        super().__init__(model_name, prompt_key, prompt_context)

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


class SummarizeChain(_BasePromptChain):
    """文本摘要链。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        prompt_key: str = "chain.summarize",
        prompt_context: Optional[PromptContext] = None,
    ) -> None:
        defaults = {"language": "中文", "instruction": "请简洁地总结以下内容，保留关键信息："}
        merged_defaults = _merge_context(defaults, prompt_context, {})
        super().__init__(model_name, prompt_key, merged_defaults)

    def _build_messages(
        self,
        text: str,
        instruction: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> list[BaseMessage]:
        final = {"text": text}
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


class TranslateChain(_BasePromptChain):
    """翻译链。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        prompt_key: str = "chain.translate",
        prompt_context: Optional[PromptContext] = None,
    ) -> None:
        defaults = {"target": "中文"}
        merged_defaults = _merge_context(defaults, prompt_context, {})
        super().__init__(model_name, prompt_key, merged_defaults)

    def _build_messages(
        self,
        text: str,
        target: Optional[str] = None,
        prompt_context: Optional[PromptContext] = None,
    ) -> list[BaseMessage]:
        final = {"text": text}
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


class ExtractionChain(_BasePromptChain):
    """结构化信息抽取链。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        prompt_key: str = "chain.extraction",
        prompt_context: Optional[PromptContext] = None,
    ) -> None:
        super().__init__(model_name, prompt_key, prompt_context)

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


class RefineChain(_BasePromptChain):
    """文本优化链。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        prompt_key: str = "chain.refine",
        prompt_context: Optional[PromptContext] = None,
    ) -> None:
        defaults = {"language": "中文"}
        merged_defaults = _merge_context(defaults, prompt_context, {})
        super().__init__(model_name, prompt_key, merged_defaults)

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
