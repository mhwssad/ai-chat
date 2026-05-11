"""基于 LangGraph 的 ReAct Agent。"""

from typing import TYPE_CHECKING, Iterator, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain.agents import create_agent

from src.ai_chat.llm import llm_factory
from src.ai_chat.tools.registry import tool_registry

if TYPE_CHECKING:
    from src.ai_chat.memory.manager import ConversationMemory


class ChatAgent:
    """ReAct Agent — 能使用工具的对话智能体。

    整合 LLM + Tools，通过 LangGraph 的 create_agent 实现
    思考 → 行动 → 观察 的循环推理。
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[list] = None,
        memory: Optional["ConversationMemory"] = None,
    ) -> None:
        self._model_name = model_name or self._get_default_model()
        self._system_prompt = system_prompt or "你是一个有帮助的 AI 助手。请用中文回答用户的问题。你可以使用工具来完成任务。"
        self._tools = tools or tool_registry.get_all()
        self._memory = memory

        provider = llm_factory.get_chat_provider(self._model_name)
        self._llm = provider.get_client(self._model_name)

        self._agent = create_agent(
            model=self._llm,
            tools=self._tools,
            system_prompt=self._system_prompt,
        )

    def invoke(self, message: str, history: Optional[list[BaseMessage]] = None) -> str:
        """同步调用，返回最终回复文本。"""
        if self._memory is not None:
            history = self._memory.load_history()

        messages = list(history) if history else []
        messages.append(HumanMessage(content=message))

        result = self._agent.invoke({"messages": messages})  # type: ignore[arg-type]
        ai_content = result["messages"][-1].content

        if self._memory is not None:
            self._memory.save_interaction(
                HumanMessage(content=message),
                AIMessage(content=ai_content),
            )

        return ai_content

    def stream(self, message: str, history: Optional[list[BaseMessage]] = None) -> Iterator[str]:
        """流式调用，逐 token 返回。"""
        if self._memory is not None:
            history = self._memory.load_history()

        messages = list(history) if history else []
        messages.append(HumanMessage(content=message))

        collected: list[str] = []
        for event in self._agent.stream({"messages": messages}, stream_mode="values"):  # type: ignore[arg-type]
            if not event.get("messages"):
                continue
            last = event["messages"][-1]
            if isinstance(last, AIMessage) and isinstance(last.content, str) and last.content:
                collected.append(last.content)
                yield last.content

        if self._memory is not None and collected:
            full_response = "".join(collected)
            self._memory.save_interaction(
                HumanMessage(content=message),
                AIMessage(content=full_response),
            )

    @staticmethod
    def _get_default_model() -> str:
        from src.ai_chat.config import settings
        return settings.model_name
