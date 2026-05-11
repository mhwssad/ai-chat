"""常用调用链 — 基于 LCEL 模式的即用型链。

每条链封装 prompt + llm + parser，通过 llm_factory 自动路由模型。
"""

from typing import Iterator, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from src.ai_chat.llm import llm_factory


# ======================================================================
# ChatChain — 简单对话（系统提示 + 用户消息）
# ======================================================================


class ChatChain:
    """简单对话链：system_prompt + 用户输入 → LLM 回复。

    Usage::

        chain = ChatChain(model_name="qwen-turbo")
        reply = chain.invoke("你好")
        reply = chain.invoke("我刚才说了什么", history=messages)
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        self._model_name = model_name or self._get_default_model()
        self._system_prompt = system_prompt
        self._llm = llm_factory.get_chat_provider(self._model_name).get_client(self._model_name)
        self._chain = self._llm | StrOutputParser()

    def invoke(self, message: str, history: Optional[list[BaseMessage]] = None) -> str:
        messages = list(history) if history else []
        if self._system_prompt:
            messages = [SystemMessage(content=self._system_prompt)] + messages
        messages.append(HumanMessage(content=message))
        return self._chain.invoke(messages)

    def stream(self, message: str, history: Optional[list[BaseMessage]] = None) -> Iterator[str]:
        messages = list(history) if history else []
        if self._system_prompt:
            messages = [SystemMessage(content=self._system_prompt)] + messages
        messages.append(HumanMessage(content=message))
        for chunk in self._chain.stream(messages):
            if chunk:
                yield chunk

    @staticmethod
    def _get_default_model() -> str:
        from src.ai_chat.config import settings
        return settings.model_name


# ======================================================================
# SummarizeChain — 文本摘要
# ======================================================================


class SummarizeChain:
    """文本摘要链：输入长文本 → 输出摘要。

    Usage::

        chain = SummarizeChain(model_name="qwen-turbo")
        summary = chain.invoke(long_text)
        summary = chain.invoke(long_text, instruction="用三句话总结")
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        language: str = "中文",
    ) -> None:
        self._model_name = model_name or self._get_default_model()
        self._language = language
        self._llm = llm_factory.get_chat_provider(self._model_name).get_client(self._model_name)
        self._chain = self._llm | StrOutputParser()

    def invoke(self, text: str, instruction: Optional[str] = None) -> str:
        system = f"你是一个专业的文本摘要助手。请用{self._language}输出摘要。"
        user = instruction or "请简洁地总结以下内容，保留关键信息："
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=f"{user}\n\n{text}"),
        ]
        return self._chain.invoke(messages)

    def stream(self, text: str, instruction: Optional[str] = None) -> Iterator[str]:
        system = f"你是一个专业的文本摘要助手。请用{self._language}输出摘要。"
        user = instruction or "请简洁地总结以下内容，保留关键信息："
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=f"{user}\n\n{text}"),
        ]
        for chunk in self._chain.stream(messages):
            if chunk:
                yield chunk

    @staticmethod
    def _get_default_model() -> str:
        from src.ai_chat.config import settings
        return settings.model_name


# ======================================================================
# TranslateChain — 翻译
# ======================================================================


class TranslateChain:
    """翻译链：输入文本 → 输出译文。

    Usage::

        chain = TranslateChain(model_name="qwen-turbo")
        result = chain.invoke("Hello world", target="中文")
        result = chain.invoke("你好世界", target="English")
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        target: str = "中文",
    ) -> None:
        self._model_name = model_name or self._get_default_model()
        self._default_target = target
        self._llm = llm_factory.get_chat_provider(self._model_name).get_client(self._model_name)
        self._chain = self._llm | StrOutputParser()

    def invoke(self, text: str, target: Optional[str] = None) -> str:
        language = target or self._default_target
        messages = [
            SystemMessage(content=f"你是一个专业翻译。请将以下文本翻译成{language}，只输出译文，不要解释。"),
            HumanMessage(content=text),
        ]
        return self._chain.invoke(messages)

    def stream(self, text: str, target: Optional[str] = None) -> Iterator[str]:
        language = target or self._default_target
        messages = [
            SystemMessage(content=f"你是一个专业翻译。请将以下文本翻译成{language}，只输出译文，不要解释。"),
            HumanMessage(content=text),
        ]
        for chunk in self._chain.stream(messages):
            if chunk:
                yield chunk

    @staticmethod
    def _get_default_model() -> str:
        from src.ai_chat.config import settings
        return settings.model_name


# ======================================================================
# ExtractionChain — 结构化信息抽取
# ======================================================================


class ExtractionChain:
    """结构化抽取链：从文本中提取指定字段，输出 JSON。

    Usage::

        chain = ExtractionChain(model_name="qwen-turbo")
        result = chain.invoke(
            "张三，男，1990年3月15日出生，住址：北京市海淀区",
            fields=["姓名", "性别", "出生日期", "住址"],
        )
    """

    def __init__(self, model_name: Optional[str] = None) -> None:
        self._model_name = model_name or self._get_default_model()
        self._llm = llm_factory.get_chat_provider(self._model_name).get_client(self._model_name)
        self._chain = self._llm | StrOutputParser()

    def invoke(self, text: str, fields: list[str]) -> str:
        fields_desc = "、".join(fields)
        messages = [
            SystemMessage(content=(
                "你是一个信息抽取助手。从用户提供的文本中提取指定字段。"
                f"需要提取的字段：{fields_desc}\n"
                "严格以 JSON 格式输出，字段名即上述名称。如果某字段在文本中找不到，值设为 null。"
                "只输出 JSON，不要输出其他内容。"
            )),
            HumanMessage(content=text),
        ]
        return self._chain.invoke(messages)

    def stream(self, text: str, fields: list[str]) -> Iterator[str]:
        fields_desc = "、".join(fields)
        messages = [
            SystemMessage(content=(
                "你是一个信息抽取助手。从用户提供的文本中提取指定字段。"
                f"需要提取的字段：{fields_desc}\n"
                "严格以 JSON 格式输出，字段名即上述名称。如果某字段在文本中找不到，值设为 null。"
                "只输出 JSON，不要输出其他内容。"
            )),
            HumanMessage(content=text),
        ]
        for chunk in self._chain.stream(messages):
            if chunk:
                yield chunk

    @staticmethod
    def _get_default_model() -> str:
        from src.ai_chat.config import settings
        return settings.model_name


# ======================================================================
# RefineChain — 迭代优化文本
# ======================================================================


class RefineChain:
    """文本优化链：按指令迭代优化文本。

    Usage::

        chain = RefineChain(model_name="qwen-turbo")
        result = chain.invoke(
            "这篇文章的结构不够清晰",
            text="（原始文本内容）",
        )
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        language: str = "中文",
    ) -> None:
        self._model_name = model_name or self._get_default_model()
        self._language = language
        self._llm = llm_factory.get_chat_provider(self._model_name).get_client(self._model_name)
        self._chain = self._llm | StrOutputParser()

    def invoke(self, instruction: str, text: str) -> str:
        messages = [
            SystemMessage(content=(
                f"你是一个专业的文本编辑。请用{self._language}输出优化后的文本。"
                "根据用户的指令对提供的文本进行优化，只输出优化后的完整文本，不要解释。"
            )),
            HumanMessage(content=f"优化指令：{instruction}\n\n原始文本：\n{text}"),
        ]
        return self._chain.invoke(messages)

    def stream(self, instruction: str, text: str) -> Iterator[str]:
        messages = [
            SystemMessage(content=(
                f"你是一个专业的文本编辑。请用{self._language}输出优化后的文本。"
                "根据用户的指令对提供的文本进行优化，只输出优化后的完整文本，不要解释。"
            )),
            HumanMessage(content=f"优化指令：{instruction}\n\n原始文本：\n{text}"),
        ]
        for chunk in self._chain.stream(messages):
            if chunk:
                yield chunk

    @staticmethod
    def _get_default_model() -> str:
        from src.ai_chat.config import settings
        return settings.model_name
