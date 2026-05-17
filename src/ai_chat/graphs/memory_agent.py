"""内置记忆的对话智能体。"""

from __future__ import annotations

from typing import Any, AsyncIterator, Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage

from src.ai_chat.graphs.base import GraphConfig, _BaseAgent
from src.ai_chat.llm import llm_factory
from src.ai_chat.prompts import render_system_prompt
from src.ai_chat.tools.registry import tool_registry

PromptContext = dict[str, Any]


class MemoryAgent(_BaseAgent):
    """自带记忆的 ReAct Agent。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        system_prompt_key: str = "agent.react.system",
        system_prompt_context: Optional[PromptContext] = None,
        tools: Optional[list] = None,
        session_id: Optional[str] = None,
        memory_config: Optional[Any] = None,
        config: Optional[GraphConfig] = None,
    ) -> None:
        super().__init__(
            model_name=model_name,
            config=config,
            session_id=session_id,
            memory_config=memory_config,
        )
        self._system_prompt_key = system_prompt_key
        self._system_prompt_context = dict(system_prompt_context or {})
        self._tools = tools or tool_registry.get_all()

        self._llm = llm_factory.get_client(self._model_name)
        self._system_prompt = render_system_prompt(
            self._system_prompt_key,
            **self._system_prompt_context,
        )
        self._agent = create_agent(
            model=self._llm,
            tools=self._tools,
            system_prompt=self._system_prompt,
        )

    async def ainvoke(self, message: str, history: Optional[list[BaseMessage]] = None, **kwargs) -> str:
        messages = self._build_messages(message)
        result = await self._agent.ainvoke({"messages": messages})
        ai_content = result["messages"][-1].content
        self._save(message, ai_content)
        return ai_content

    async def astream(self, message: str, history: Optional[list[BaseMessage]] = None, **kwargs) -> AsyncIterator[str]:
        messages = self._build_messages(message)
        collected: list[str] = []
        seen_ids: set[str] = set()
        async for event in self._agent.astream(
            {"messages": messages}, stream_mode="values"
        ):
            if not event.get("messages"):
                continue
            last = event["messages"][-1]
            if (
                isinstance(last, AIMessage)
                and isinstance(last.content, str)
                and last.content
                and last.id not in seen_ids
            ):
                seen_ids.add(last.id)
                collected.append(last.content)
                yield last.content

        if collected:
            self._save(message, "".join(collected))
