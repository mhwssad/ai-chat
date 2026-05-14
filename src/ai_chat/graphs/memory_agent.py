"""内置记忆的对话智能体。"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Iterator, Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.ai_chat.llm import llm_factory
from src.ai_chat.memory import ConversationMemory, MemoryConfig
from src.ai_chat.prompts import render_system_prompt
from src.ai_chat.tools.registry import tool_registry


PromptContext = dict[str, Any]


class MemoryAgent:
    """自带记忆的 ReAct Agent。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        system_prompt_key: str = "agent.react.system",
        system_prompt_context: Optional[PromptContext] = None,
        tools: Optional[list] = None,
        session_id: Optional[str] = None,
        memory_config: Optional[MemoryConfig] = None,
    ) -> None:
        self._model_name = model_name or self._get_default_model()
        self._system_prompt_key = system_prompt_key
        self._system_prompt_context = dict(system_prompt_context or {})
        self._tools = tools or tool_registry.get_all()

        provider = llm_factory.get_chat_provider(self._model_name)
        self._llm = provider.get_client(self._model_name)
        self._system_prompt = render_system_prompt(
            self._system_prompt_key,
            **self._system_prompt_context,
        )
        self._agent = create_agent(
            model=self._llm,
            tools=self._tools,
            system_prompt=self._system_prompt,
        )

        self._memory = ConversationMemory(
            session_id=session_id,
            config=memory_config,
        )

    @property
    def session_id(self) -> str:
        return self._memory.session_id

    def _build_messages(self, message: str) -> list[BaseMessage]:
        history = self._memory.load_history()
        messages = list(history)
        messages.append(HumanMessage(content=message))
        return messages

    def _save(self, message: str, ai_content: str) -> None:
        self._memory.save_interaction(
            HumanMessage(content=message),
            AIMessage(content=ai_content),
        )

    async def ainvoke(self, message: str) -> str:
        messages = self._build_messages(message)
        result = await self._agent.ainvoke({"messages": messages})  # type: ignore[arg-type]
        ai_content = result["messages"][-1].content
        self._save(message, ai_content)
        return ai_content

    async def astream(self, message: str) -> AsyncIterator[str]:
        messages = self._build_messages(message)
        collected: list[str] = []
        async for event in self._agent.astream({"messages": messages}, stream_mode="values"):  # type: ignore[arg-type]
            if not event.get("messages"):
                continue
            last = event["messages"][-1]
            if isinstance(last, AIMessage) and isinstance(last.content, str) and last.content:
                collected.append(last.content)
                yield last.content

        if collected:
            self._save(message, "".join(collected))

    def invoke(self, message: str) -> str:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        else:
            loop = True

        if loop:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, self.ainvoke(message)).result()
        return asyncio.run(self.ainvoke(message))

    def stream(self, message: str) -> Iterator[str]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        else:
            loop = True

        async def _collect():
            chunks = []
            async for chunk in self.astream(message):
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

    def chat(self) -> None:
        print(f"会话 ID: {self.session_id}")
        print("输入 'quit' 或 'exit' 退出\n")

        while True:
            user_input = input("你: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit"):
                print("再见！")
                break
            response = self.invoke(user_input)
            print(f"AI: {response}\n")

    def clear(self) -> None:
        self._memory.clear()

    def get_summary(self) -> Optional[str]:
        return self._memory.get_summary()

    def get_message_count(self) -> int:
        return self._memory.get_message_count()

    @staticmethod
    def _get_default_model() -> str:
        from src.ai_chat.config import settings

        return settings.model_name
