"""LangChain 适配工具。"""

from __future__ import annotations

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from src.ai.exception.llm_exception import LLMException

from ..types import ChatMessage
from ..usage import UsageCalculator


def to_langchain_messages(messages: list[ChatMessage]) -> list[BaseMessage]:
    converted: list[BaseMessage] = []
    for message in messages:
        if message.role == "system":
            converted.append(SystemMessage(content=message.content))
        elif message.role == "assistant":
            converted.append(AIMessage(content=message.content))
        elif message.role == "tool":
            converted.append(ToolMessage(content=message.content, tool_call_id="tool"))
        else:
            converted.append(HumanMessage(content=message.content))
    return converted


def ai_message_text(message: AIMessage | AIMessageChunk) -> str:
    return message.text()


def ensure_ai_message(value: object) -> AIMessage | AIMessageChunk:
    if not isinstance(value, (AIMessage, AIMessageChunk)):
        raise LLMException("LangChain 返回了非 AIMessage 响应")
    return value


def request_id_from_ai_message(message: AIMessage | AIMessageChunk) -> str | None:
    response_metadata = getattr(message, "response_metadata", None) or {}
    return (
        response_metadata.get("id")
        or response_metadata.get("request_id")
        or response_metadata.get("system_fingerprint")
    )


usage_calculator = UsageCalculator()
