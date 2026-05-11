"""ConversationMemory — 管理短期缓冲 + 长期摘要的高层编排器。"""

from datetime import datetime
from typing import Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from src.ai_chat.memory.factory import memory_factory
from src.ai_chat.memory.models import (
    MemoryConfig,
    MemoryProvider,
    Session,
    message_to_record,
    record_to_message,
)


def memory_config_from_settings() -> MemoryConfig:
    """从全局 Settings 构建 MemoryConfig。"""
    from src.ai_chat.config import settings

    return MemoryConfig(
        backend=settings.memory_backend,
        persist_path=settings.memory_persist_path or None,
        max_short_term_messages=settings.memory_max_short_term_messages,
        summary_model=settings.memory_summary_model or None,
        summary_token_limit=settings.memory_summary_token_limit,
        enable_summary=settings.memory_enable_summary,
    )


class ConversationMemory:
    """单会话的上下文记忆管理器。

    Usage::

        memory = ConversationMemory()
        history = memory.load_history()
        memory.save_interaction(human_msg, ai_msg)
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        config: Optional[MemoryConfig] = None,
        provider: Optional[MemoryProvider] = None,
    ) -> None:
        self._config = config or memory_config_from_settings()
        self._store = provider or memory_factory.create(
            self._config.backend, self._config
        )
        if session_id:
            try:
                self._session = self._store.get_session(session_id)
            except Exception:
                self._session = self._store.create_session(session_id)
        else:
            self._session = self._store.create_session()

    @property
    def session_id(self) -> str:
        return self._session.session_id

    @property
    def session(self) -> Session:
        return self._session

    def load_history(self) -> list[BaseMessage]:
        """加载 LLM 上下文：[摘要 SystemMessage?] + 最近 N 条消息。"""
        messages: list[BaseMessage] = []

        if self._config.enable_summary:
            summary = self._store.load_summary(self.session_id)
            if summary:
                messages.append(
                    SystemMessage(content=f"之前的对话摘要：\n{summary}")
                )

        total = self._store.count_messages(self.session_id)
        limit = min(self._config.max_short_term_messages, total)
        offset = total - limit if total > self._config.max_short_term_messages else 0
        records = self._store.get_messages(self.session_id, limit=limit, offset=offset)
        for rec in records:
            messages.append(record_to_message(rec))

        return messages

    def save_interaction(
        self,
        human_message: BaseMessage,
        ai_message: BaseMessage,
    ) -> None:
        """持久化一轮对话并触发摘要检查。"""
        self._store.add_message(message_to_record(human_message, self.session_id))
        self._store.add_message(message_to_record(ai_message, self.session_id))
        self._session.updated_at = datetime.now()

        if self._config.enable_summary:
            self._maybe_summarize()

    def save_message(self, message: BaseMessage) -> None:
        """持久化单条消息。"""
        self._store.add_message(message_to_record(message, self.session_id))
        self._session.updated_at = datetime.now()

    def clear(self) -> None:
        """删除当前会话及所有数据。"""
        self._store.delete_session(self.session_id)

    def get_message_count(self) -> int:
        return self._store.count_messages(self.session_id)

    def get_summary(self) -> Optional[str]:
        return self._store.load_summary(self.session_id)

    def _maybe_summarize(self) -> None:
        """消息数超过 2 倍窗口时，对超出窗口的旧消息生成摘要。"""
        total = self._store.count_messages(self.session_id)
        threshold = self._config.max_short_term_messages * 2
        if total < threshold:
            return

        overflow_count = total - self._config.max_short_term_messages
        old_records = self._store.get_messages(
            self.session_id, limit=overflow_count, offset=0
        )
        old_messages = [record_to_message(r) for r in old_records]
        summary = self._generate_summary(old_messages)
        if summary:
            existing = self._store.load_summary(self.session_id) or ""
            combined = f"{existing}\n\n---\n\n{summary}" if existing else summary
            self._store.save_summary(self.session_id, combined)

    def _generate_summary(self, messages: list[BaseMessage]) -> Optional[str]:
        """调用 LLM 对消息列表生成摘要。"""
        from src.ai_chat.llm import llm_factory

        model_name = self._config.summary_model
        if model_name is None:
            from src.ai_chat.config import settings

            model_name = settings.model_name

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
                        f"摘要控制在 {self._config.summary_token_limit} token 以内。"
                    )
                ),
                HumanMessage(content=conversation_text),
            ]
            result = client.invoke(prompt_messages)
            return result.content if isinstance(result.content, str) else str(result.content)
        except Exception:
            return None
