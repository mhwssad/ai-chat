"""对话摘要链 — 将对话消息压缩为摘要。"""

from __future__ import annotations

from typing import Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from src.ai_chat.llm import llm_factory


class ConversationSummaryChain:
    """将对话历史压缩为简洁摘要，保留关键事实和上下文。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        token_limit: int = 500,
    ) -> None:
        self._model_name = model_name
        self._token_limit = token_limit

    def invoke(self, messages: list[BaseMessage]) -> Optional[str]:
        """对消息列表生成摘要。"""
        model_name = self._model_name or self._get_default_model()

        try:
            provider = llm_factory.get_chat_provider(model_name)
            client = provider.get_client(model_name)

            conversation_text = "\n".join(
                f"{msg.type}: {msg.content}" for msg in messages
            )
            prompt_messages = [
                SystemMessage(
                    content=(
                        "你是一个对话摘要助手。请简洁地总结以下对话，"
                        "保留关键事实、决定和上下文信息。"
                        f"摘要控制在 {self._token_limit} token 以内。"
                    )
                ),
                HumanMessage(content=conversation_text),
            ]
            result = client.invoke(prompt_messages)
            return result.content if isinstance(result.content, str) else str(result.content)
        except Exception:
            return None

    @staticmethod
    def _get_default_model() -> str:
        from src.ai_chat.config import settings
        return settings.model_name
