"""基于 LangGraph 的 ReAct Agent。"""

from __future__ import annotations

from typing import Any, AsyncIterator, Iterator, Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage

from src.ai_chat.graphs.base import (
    GraphConfig,
    _BaseAgent,
    merge_context,
)
from src.ai_chat.llm import llm_factory
from src.ai_chat.prompts import render_system_prompt
from src.ai_chat.tools.registry import tool_registry

PromptContext = dict[str, Any]


class ChatAgent(_BaseAgent):
    """ReAct Agent — 能使用工具的对话智能体。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        system_prompt_key: str = "agent.react.system",
        system_prompt_context: Optional[PromptContext] = None,
        tools: Optional[list] = None,
        memory: Optional[Any] = None,
        config: Optional[GraphConfig] = None,
    ) -> None:
        super().__init__(model_name=model_name, config=config, memory=memory)
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

    def _resolve_system_prompt(
        self,
        system_prompt_override: Optional[str] = None,
        system_prompt_context_override: Optional[PromptContext] = None,
    ) -> str:
        if system_prompt_override is not None:
            return system_prompt_override
        context = merge_context(
            self._system_prompt_context, system_prompt_context_override
        )
        return render_system_prompt(self._system_prompt_key, **context)

    def _build_temp_agent(
        self,
        system_prompt_override: Optional[str] = None,
        tools_override: Optional[list] = None,
        model_override: Optional[str] = None,
        system_prompt_context_override: Optional[PromptContext] = None,
    ):
        model_name = model_override or self._model_name
        tools = tools_override if tools_override is not None else self._tools
        system = self._resolve_system_prompt(
            system_prompt_override, system_prompt_context_override
        )

        if model_override and model_override != self._model_name:
            llm = llm_factory.get_client(model_name)
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
        system_prompt_context_override: Optional[PromptContext] = None,
        **kwargs,
    ) -> str:
        messages = self._build_messages(message, history)
        if (
            system_prompt_override
            or tools_override
            or model_override
            or system_prompt_context_override
        ):
            agent = self._build_temp_agent(
                system_prompt_override,
                tools_override,
                model_override,
                system_prompt_context_override,
            )
        else:
            agent = self._agent

        result = await agent.ainvoke({"messages": messages})
        ai_content = result["messages"][-1].content
        self._save(message, ai_content)
        return ai_content

    async def astream(
        self,
        message: str,
        history: Optional[list[BaseMessage]] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        messages = self._build_messages(message, history)
        collected: list[str] = []
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
            ):
                collected.append(last.content)
                yield last.content

        if collected:
            self._save(message, "".join(collected))

    def invoke(
        self,
        message: str,
        history: Optional[list[BaseMessage]] = None,
        system_prompt_override: Optional[str] = None,
        tools_override: Optional[list] = None,
        model_override: Optional[str] = None,
        system_prompt_context_override: Optional[PromptContext] = None,
        **kwargs,
    ) -> str:
        return self._run_async(self.ainvoke(
            message, history,
            system_prompt_override, tools_override,
            model_override, system_prompt_context_override,
        ))

    def stream(
        self, message: str, history: Optional[list[BaseMessage]] = None, **kwargs,
    ) -> Iterator[str]:
        yield from self._run_async_iterator(self.astream(message, history))
