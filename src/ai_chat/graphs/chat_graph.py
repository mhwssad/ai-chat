"""基于 LangGraph StateGraph 的多步骤对话图。

流程：用户输入 → 分类意图 → 条件路由 → {chat / rag} → 结束
"""

from typing import Annotated, Iterator, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.ai_chat.llm import llm_factory
from src.ai_chat.rag import rag_factory


class ChatGraphState(TypedDict):
    """图状态 — 节点间流转的数据。"""

    messages: Annotated[list[BaseMessage], add_messages]
    intent: str
    context: str


_CLASSIFY_PROMPT = """\
你是一个意图分类器。根据用户消息判断意图，只回答一个词：

- "rag"：用户在询问事实性问题，需要检索知识库来回答
- "chat"：普通聊天、问候、创意写作、关于你自身的问题

只回答 "rag" 或 "chat"，不要输出其他内容。"""

_RAG_SYSTEM = "你是一个有帮助的 AI 助手。请根据提供的参考资料回答用户问题。如果资料中没有相关信息，请说明。请用中文回答。"


class ChatGraph:
    """多步骤对话图 — 意图分类 → 条件路由 → 分支处理。"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        rag_store_name: str = "faiss",
        rag_k: int = 4,
    ) -> None:
        self._model_name = model_name or self._get_default_model()
        self._system_prompt = system_prompt or "你是一个有帮助的 AI 助手。请用中文回答用户的问题。"
        self._rag_store = rag_factory.create_store(rag_store_name)
        self._rag_k = rag_k

        provider = llm_factory.get_chat_provider(self._model_name)
        self._llm = provider.get_client(self._model_name)

        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(ChatGraphState)

        workflow.add_node("classify", self._make_classify_node())
        workflow.add_node("chat", self._make_chat_node())
        workflow.add_node("rag", self._make_rag_node())

        workflow.add_edge(START, "classify")
        workflow.add_conditional_edges(
            "classify",
            _route_by_intent,
            {"chat": "chat", "rag": "rag"},
        )
        workflow.add_edge("chat", END)
        workflow.add_edge("rag", END)

        return workflow.compile()

    # ── 节点工厂 ───────────────────────────────────────

    def _make_classify_node(self):
        llm = self._llm

        def classify(state: ChatGraphState) -> dict:
            messages = state["messages"]
            question = ""
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    question = msg.content if isinstance(msg.content, str) else str(msg.content)
                    break

            classify_messages = [
                SystemMessage(content=_CLASSIFY_PROMPT),
                HumanMessage(content=question),
            ]
            result = llm.invoke(classify_messages)
            intent = result.content.strip().lower() if isinstance(result.content, str) else "chat"
            if intent not in ("chat", "rag"):
                intent = "chat"

            return {"intent": intent}

        return classify

    def _make_chat_node(self):
        llm = self._llm
        system_prompt = self._system_prompt

        def chat(state: ChatGraphState) -> dict:
            messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
            result = llm.invoke(messages)
            return {"messages": [result]}

        return chat

    def _make_rag_node(self):
        llm = self._llm
        store = self._rag_store
        rag_k = self._rag_k

        def rag(state: ChatGraphState) -> dict:
            messages = state["messages"]
            question = ""
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    question = msg.content if isinstance(msg.content, str) else str(msg.content)
                    break

            docs = store.similarity_search(question, k=rag_k)
            context = "\n\n".join(d["content"] for d in docs)

            rag_prompt = (
                f"参考资料：\n{context}\n\n"
                f"用户问题：{question}\n\n"
                "请根据参考资料回答用户问题。如果资料中没有相关信息，请说明。"
            )
            rag_messages = [
                SystemMessage(content=_RAG_SYSTEM),
                HumanMessage(content=rag_prompt),
            ]
            result = llm.invoke(rag_messages)
            return {"context": context, "messages": [result]}

        return rag

    # ── 公共接口 ───────────────────────────────────────

    def invoke(self, message: str, history: Optional[list[BaseMessage]] = None) -> str:
        """同步调用，返回最终回复文本。"""
        messages = list(history) if history else []
        messages.append(HumanMessage(content=message))

        result = self._graph.invoke({"messages": messages, "intent": "", "context": ""})  # type: ignore[arg-type]
        return result["messages"][-1].content

    def stream(self, message: str, history: Optional[list[BaseMessage]] = None) -> Iterator[str]:
        """流式调用，逐 token 返回。"""
        messages = list(history) if history else []
        messages.append(HumanMessage(content=message))

        seen_ids: set[str] = set()
        for event in self._graph.stream(
            {"messages": messages, "intent": "", "context": ""},  # type: ignore[arg-type]
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
                yield last.content

    @staticmethod
    def _get_default_model() -> str:
        from src.ai_chat.config import settings
        return settings.model_name


def _route_by_intent(state: ChatGraphState) -> str:
    """条件路由 — 根据分类结果选择处理节点。"""
    return state.get("intent", "") or "chat"
