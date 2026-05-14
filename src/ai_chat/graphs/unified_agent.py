"""整合所有功能的统一对话智能体。"""

from __future__ import annotations

import asyncio
from typing import Any, Annotated, AsyncIterator, Iterator, Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.ai_chat.llm import llm_factory
from src.ai_chat.memory import ConversationMemory, MemoryConfig
from src.ai_chat.prompts import render_messages, render_system_prompt
from src.ai_chat.rag import rag_factory
from src.ai_chat.tools.registry import tool_registry


PromptContext = dict[str, Any]


class UnifiedState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    intent: str
    context: str


def _merge_context(
    base: Optional[PromptContext],
    override: Optional[PromptContext],
    final: Optional[PromptContext] = None,
) -> PromptContext:
    context: PromptContext = {}
    if base:
        context.update(base)
    if override:
        context.update(override)
    if final:
        context.update(final)
    return context


class UnifiedAgent:
    """整合记忆 + 工具 + RAG 的统一智能体。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        react_prompt_key: str = "agent.react.system",
        react_prompt_context: Optional[PromptContext] = None,
        classify_prompt_key: str = "graph.intent.react_or_rag",
        classify_prompt_context: Optional[PromptContext] = None,
        rag_prompt_key: str = "graph.rag.answer",
        rag_prompt_context: Optional[PromptContext] = None,
        tools: Optional[list] = None,
        session_id: Optional[str] = None,
        memory_config: Optional[MemoryConfig] = None,
        rag_store_name: str = "faiss",
        rag_k: int = 4,
    ) -> None:
        self._model_name = model_name or self._get_default_model()
        self._react_prompt_key = react_prompt_key
        self._react_prompt_context = dict(react_prompt_context or {})
        self._classify_prompt_key = classify_prompt_key
        self._classify_prompt_context = dict(classify_prompt_context or {})
        self._rag_prompt_key = rag_prompt_key
        self._rag_prompt_context = dict(rag_prompt_context or {})
        self._tools = tools or tool_registry.get_all()
        self._rag_store = rag_factory.create_store(rag_store_name)
        self._rag_k = rag_k

        provider = llm_factory.get_chat_provider(self._model_name)
        self._llm = provider.get_client(self._model_name)
        self._react_system_prompt = render_system_prompt(
            self._react_prompt_key,
            **self._react_prompt_context,
        )
        self._react_agent = create_agent(
            model=self._llm,
            tools=self._tools,
            system_prompt=self._react_system_prompt,
        )
        self._memory = ConversationMemory(session_id=session_id, config=memory_config)
        self._graph = self._build_graph()

    @property
    def session_id(self) -> str:
        return self._memory.session_id

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(UnifiedState)
        workflow.add_node("classify", self._make_classify_node())
        workflow.add_node("react", self._make_react_node())
        workflow.add_node("rag", self._make_rag_node())
        workflow.add_edge(START, "classify")
        workflow.add_conditional_edges("classify", _route_by_intent, {"react": "react", "rag": "rag"})
        workflow.add_edge("react", END)
        workflow.add_edge("rag", END)
        return workflow.compile()

    def _make_classify_node(self):
        llm = self._llm
        prompt_key = self._classify_prompt_key
        prompt_context = self._classify_prompt_context

        def classify(state: UnifiedState) -> dict:
            question = _extract_last_human_message(state["messages"])
            messages = render_messages(
                prompt_key,
                **_merge_context(prompt_context, None, {"question": question}),
            )
            result = llm.invoke(messages)
            intent = result.content.strip().lower() if isinstance(result.content, str) else "react"
            if intent not in ("react", "rag"):
                intent = "react"
            return {"intent": intent}

        return classify

    def _make_react_node(self):
        agent = self._react_agent

        async def react(state: UnifiedState) -> dict:
            result = await agent.ainvoke({"messages": state["messages"]})  # type: ignore[arg-type]
            return {"messages": result["messages"]}

        return react

    def _make_rag_node(self):
        llm = self._llm
        store = self._rag_store
        rag_k = self._rag_k
        prompt_key = self._rag_prompt_key
        prompt_context = self._rag_prompt_context

        def rag(state: UnifiedState) -> dict:
            question = _extract_last_human_message(state["messages"])
            docs = store.similarity_search(question, k=rag_k)
            context_text = "\n\n".join(d["content"] for d in docs)
            messages = render_messages(
                prompt_key,
                **_merge_context(
                    prompt_context,
                    None,
                    {"context": context_text, "question": question},
                ),
            )
            result = llm.invoke(messages)
            return {"context": context_text, "messages": [result]}

        return rag

    def _build_messages(self, message: str) -> list[BaseMessage]:
        history = self._memory.load_history()
        messages = list(history)
        messages.append(HumanMessage(content=message))
        return messages

    def _save(self, message: str, ai_content: str) -> None:
        self._memory.save_interaction(HumanMessage(content=message), AIMessage(content=ai_content))

    def _resolve_react_system_prompt(
        self,
        system_prompt_override: Optional[str],
        react_prompt_context_override: Optional[PromptContext] = None,
    ) -> str:
        if system_prompt_override is not None:
            return system_prompt_override
        context = _merge_context(self._react_prompt_context, react_prompt_context_override)
        return render_system_prompt(self._react_prompt_key, **context)

    async def ainvoke(
        self,
        message: str,
        system_prompt_override: Optional[str] = None,
        tools_override: Optional[list] = None,
        model_override: Optional[str] = None,
        react_prompt_context_override: Optional[PromptContext] = None,
    ) -> str:
        messages = self._build_messages(message)

        if system_prompt_override or tools_override or model_override or react_prompt_context_override:
            model_name = model_override or self._model_name
            tools = tools_override if tools_override is not None else self._tools
            system = self._resolve_react_system_prompt(
                system_prompt_override,
                react_prompt_context_override,
            )

            if model_override and model_override != self._model_name:
                provider = llm_factory.get_chat_provider(model_name)
                llm = provider.get_client(model_name)
            else:
                llm = self._llm

            temp_agent = create_agent(model=llm, tools=tools, system_prompt=system)
            result = await temp_agent.ainvoke({"messages": messages})  # type: ignore[arg-type]
        else:
            result = await self._graph.ainvoke({"messages": messages, "intent": "", "context": ""})  # type: ignore[arg-type]

        ai_content = result["messages"][-1].content
        self._save(message, ai_content)
        return ai_content

    async def astream(self, message: str) -> AsyncIterator[str]:
        messages = self._build_messages(message)
        seen_ids: set[str] = set()
        collected: list[str] = []
        async for event in self._graph.astream(
            {"messages": messages, "intent": "", "context": ""},
            stream_mode="values",
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

    def invoke(
        self,
        message: str,
        system_prompt_override: Optional[str] = None,
        tools_override: Optional[list] = None,
        model_override: Optional[str] = None,
        react_prompt_context_override: Optional[PromptContext] = None,
    ) -> str:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        else:
            loop = True

        coro = self.ainvoke(
            message,
            system_prompt_override,
            tools_override,
            model_override,
            react_prompt_context_override,
        )
        if loop:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return asyncio.run(coro)

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


def _extract_last_human_message(messages: list[BaseMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content if isinstance(msg.content, str) else str(msg.content)
    return ""


def _route_by_intent(state: UnifiedState) -> str:
    return state.get("intent", "") or "react"
