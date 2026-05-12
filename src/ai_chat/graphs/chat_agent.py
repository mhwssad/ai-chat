"""基于 LangGraph 的 ReAct Agent。"""

import asyncio
from typing import TYPE_CHECKING, AsyncIterator, Iterator, Optional

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

    def _build_messages(self, message: str, history: Optional[list[BaseMessage]] = None) -> list[BaseMessage]:
        if self._memory is not None:
            history = self._memory.load_history()
        messages = list(history) if history else []
        messages.append(HumanMessage(content=message))
        return messages

    def _save_if_needed(self, message: str, ai_content: str) -> None:
        if self._memory is not None:
            self._memory.save_interaction(
                HumanMessage(content=message),
                AIMessage(content=ai_content),
            )

    def _build_temp_agent(self, system_prompt_override=None, tools_override=None, model_override=None):
        """根据覆盖参数创建临时 Agent。"""
        from langchain.agents import create_agent

        model_name = model_override or self._model_name
        tools = tools_override if tools_override is not None else self._tools
        system = system_prompt_override or self._system_prompt

        if model_override and model_override != self._model_name:
            provider = llm_factory.get_chat_provider(model_override)
            llm = provider.get_client(model_override)
        else:
            llm = self._llm

        return create_agent(model=llm, tools=tools, system_prompt=system)

    async def ainvoke(
        self,
        message: str,
        history: Optional[list[BaseMessage]] = None,
        system_prompt_override: Optional[str] = None,
        tools_override: Optional[list] = None,
        model_override: Optional[str] = None,
    ) -> str:
        """异步调用，返回最终回复文本。"""
        messages = self._build_messages(message, history)

        if system_prompt_override or tools_override or model_override:
            agent = self._build_temp_agent(system_prompt_override, tools_override, model_override)
        else:
            agent = self._agent

        result = await agent.ainvoke({"messages": messages})  # type: ignore[arg-type]
        ai_content = result["messages"][-1].content
        self._save_if_needed(message, ai_content)
        return ai_content

    async def astream(self, message: str, history: Optional[list[BaseMessage]] = None) -> AsyncIterator[str]:
        """异步流式调用，逐 token 返回。"""
        messages = self._build_messages(message, history)
        collected: list[str] = []
        async for event in self._agent.astream({"messages": messages}, stream_mode="values"):  # type: ignore[arg-type]
            if not event.get("messages"):
                continue
            last = event["messages"][-1]
            if isinstance(last, AIMessage) and isinstance(last.content, str) and last.content:
                collected.append(last.content)
                yield last.content

        if collected:
            self._save_if_needed(message, "".join(collected))

    def invoke(
        self,
        message: str,
        history: Optional[list[BaseMessage]] = None,
        system_prompt_override: Optional[str] = None,
        tools_override: Optional[list] = None,
        model_override: Optional[str] = None,
    ) -> str:
        """同步调用，返回最终回复文本。"""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        else:
            loop = True

        coro = self.ainvoke(message, history, system_prompt_override, tools_override, model_override)
        if loop:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        else:
            return asyncio.run(coro)

    def stream(self, message: str, history: Optional[list[BaseMessage]] = None) -> Iterator[str]:
        """同步流式调用，逐 token 返回。"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        async def _collect():
            chunks = []
            async for chunk in self.astream(message, history):
                chunks.append(chunk)
            return chunks

        if loop:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                for chunk in pool.submit(asyncio.run, _collect()).result():
                    yield chunk
        else:
            for chunk in asyncio.run(_collect()):
                yield chunk

    @staticmethod
    def _get_default_model() -> str:
        from src.ai_chat.config import settings
        return settings.model_name
