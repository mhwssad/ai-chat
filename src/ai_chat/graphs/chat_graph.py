"""基于 LangGraph StateGraph 的多步骤对话图。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Annotated, Iterator, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.ai_chat.llm import llm_factory
from src.ai_chat.prompts import render_messages, render_system_prompt
from src.ai_chat.rag import rag_factory

if TYPE_CHECKING:
    from src.ai_chat.memory.manager import ConversationMemory


PromptContext = dict[str, Any]


class ChatGraphState(TypedDict):
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


class ChatGraph:
    """多步骤对话图 — 意图分类 → 条件路由 → 分支处理。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        classify_prompt_key: str = "graph.intent.chat_or_rag",
        classify_prompt_context: Optional[PromptContext] = None,
        chat_prompt_key: str = "graph.chat.system",
        chat_prompt_context: Optional[PromptContext] = None,
        rag_prompt_key: str = "graph.rag.answer",
        rag_prompt_context: Optional[PromptContext] = None,
        rag_store_name: str = "faiss",
        rag_k: int = 4,
        memory: Optional["ConversationMemory"] = None,
    ) -> None:
        self._model_name = model_name or self._get_default_model()
        self._classify_prompt_key = classify_prompt_key
        self._classify_prompt_context = dict(classify_prompt_context or {})
        self._chat_prompt_key = chat_prompt_key
        self._chat_prompt_context = dict(chat_prompt_context or {})
        self._rag_prompt_key = rag_prompt_key
        self._rag_prompt_context = dict(rag_prompt_context or {})
        self._rag_store = rag_factory.create_store(rag_store_name)
        self._rag_k = rag_k
        self._memory = memory

        provider = llm_factory.get_chat_provider(self._model_name)
        self._llm = provider.get_client(self._model_name)
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(ChatGraphState)
        workflow.add_node("classify", self._make_classify_node())
        workflow.add_node("chat", self._make_chat_node())
        workflow.add_node("rag", self._make_rag_node())
        workflow.add_edge(START, "classify")
        workflow.add_conditional_edges("classify", _route_by_intent, {"chat": "chat", "rag": "rag"})
        workflow.add_edge("chat", END)
        workflow.add_edge("rag", END)
        return workflow.compile()

    def _make_classify_node(self):
        llm = self._llm
        prompt_key = self._classify_prompt_key
        prompt_context = self._classify_prompt_context

        def classify(state: ChatGraphState) -> dict:
            question = _extract_last_human_message(state["messages"])
            messages = render_messages(
                prompt_key,
                **_merge_context(prompt_context, None, {"question": question}),
            )
            result = llm.invoke(messages)
            intent = result.content.strip().lower() if isinstance(result.content, str) else "chat"
            if intent not in ("chat", "rag"):
                intent = "chat"
            return {"intent": intent}

        return classify

    def _make_chat_node(self):
        llm = self._llm
        system_prompt = render_system_prompt(self._chat_prompt_key, **self._chat_prompt_context)

        def chat(state: ChatGraphState) -> dict:
            messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
            result = llm.invoke(messages)
            return {"messages": [result]}

        return chat

    def _make_rag_node(self):
        llm = self._llm
        store = self._rag_store
        rag_k = self._rag_k
        prompt_key = self._rag_prompt_key
        prompt_context = self._rag_prompt_context

        def rag(state: ChatGraphState) -> dict:
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

    def invoke(self, message: str, history: Optional[list[BaseMessage]] = None) -> str:
        if self._memory is not None:
            history = self._memory.load_history()

        messages = list(history) if history else []
        messages.append(HumanMessage(content=message))
        result = self._graph.invoke({"messages": messages, "intent": "", "context": ""})  # type: ignore[arg-type]
        ai_content = result["messages"][-1].content

        if self._memory is not None:
            self._memory.save_interaction(HumanMessage(content=message), AIMessage(content=ai_content))
        return ai_content

    def stream(self, message: str, history: Optional[list[BaseMessage]] = None) -> Iterator[str]:
        if self._memory is not None:
            history = self._memory.load_history()

        messages = list(history) if history else []
        messages.append(HumanMessage(content=message))

        seen_ids: set[str] = set()
        collected: list[str] = []
        for event in self._graph.stream(
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

        if self._memory is not None and collected:
            self._memory.save_interaction(
                HumanMessage(content=message),
                AIMessage(content="".join(collected)),
            )

    @staticmethod
    def _get_default_model() -> str:
        from src.ai_chat.config import settings

        return settings.model_name


def _extract_last_human_message(messages: list[BaseMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content if isinstance(msg.content, str) else str(msg.content)
    return ""


def _route_by_intent(state: ChatGraphState) -> str:
    return state.get("intent", "") or "chat"
