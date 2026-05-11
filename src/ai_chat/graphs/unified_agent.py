"""整合所有功能的统一对话智能体 — 记忆 + 工具 + RAG + 意图路由。"""

from typing import Annotated, Iterator, Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.ai_chat.llm import llm_factory
from src.ai_chat.memory import ConversationMemory, MemoryConfig
from src.ai_chat.prompts import prompt_registry
from src.ai_chat.rag import rag_factory
from src.ai_chat.tools.registry import tool_registry


class UnifiedState(TypedDict):
    """图状态 — 节点间流转的数据。"""

    messages: Annotated[list[BaseMessage], add_messages]
    intent: str
    context: str


_CLASSIFY_PROMPT = """\
你是一个意图分类器。根据用户消息判断意图，只回答一个词：

- "rag"：用户在询问事实性问题，需要检索知识库来回答
- "react"：普通聊天、问候、创意写作、关于你自身的问题、需要使用工具完成操作

只回答 "rag" 或 "react"，不要输出其他内容。"""

_RAG_SYSTEM = "你是一个有帮助的 AI 助手。请根据提供的参考资料回答用户问题。如果资料中没有相关信息，请说明。请用中文回答。"


class UnifiedAgent:
    """整合记忆 + 工具 + RAG 的统一智能体。

    使用 LangGraph StateGraph 实现意图分类路由：
    - react 路径：ReAct agent，支持工具调用和普通对话
    - rag 路径：检索知识库后生成回答

    内置 ConversationMemory，自动管理上下文。

    Usage::

        agent = UnifiedAgent(model_name="qwen-turbo")
        agent.chat()  # 进入交互式多轮对话
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[list] = None,
        session_id: Optional[str] = None,
        memory_config: Optional[MemoryConfig] = None,
        rag_store_name: str = "faiss",
        rag_k: int = 4,
    ) -> None:
        self._model_name = model_name or self._get_default_model()
        if system_prompt:
            self._system_prompt = system_prompt
        elif "chat" in prompt_registry:
            self._system_prompt = str(prompt_registry.get("chat").format_messages()[0].content)
        else:
            self._system_prompt = "你是一个有帮助的 AI 助手。请用中文回答用户的问题。你可以使用工具来完成任务。"
        self._tools = tools or tool_registry.get_all()
        self._rag_store = rag_factory.create_store(rag_store_name)
        self._rag_k = rag_k

        provider = llm_factory.get_chat_provider(self._model_name)
        self._llm = provider.get_client(self._model_name)

        self._react_agent = create_agent(
            model=self._llm,
            tools=self._tools,
            system_prompt=self._system_prompt,
        )

        self._memory = ConversationMemory(
            session_id=session_id,
            config=memory_config,
        )

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
        workflow.add_conditional_edges(
            "classify",
            _route_by_intent,
            {"react": "react", "rag": "rag"},
        )
        workflow.add_edge("react", END)
        workflow.add_edge("rag", END)

        return workflow.compile()

    # ── 节点工厂 ───────────────────────────────────────

    def _make_classify_node(self):
        llm = self._llm

        def classify(state: UnifiedState) -> dict:
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
            intent = result.content.strip().lower() if isinstance(result.content, str) else "react"
            if intent not in ("react", "rag"):
                intent = "react"

            return {"intent": intent}

        return classify

    def _make_react_node(self):
        agent = self._react_agent

        def react(state: UnifiedState) -> dict:
            result = agent.invoke({"messages": state["messages"]})  # type: ignore[arg-type]
            return {"messages": result["messages"]}

        return react

    def _make_rag_node(self):
        llm = self._llm
        store = self._rag_store
        rag_k = self._rag_k
        use_registry = "rag" in prompt_registry

        def rag(state: UnifiedState) -> dict:
            messages = state["messages"]
            question = ""
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    question = msg.content if isinstance(msg.content, str) else str(msg.content)
                    break

            docs = store.similarity_search(question, k=rag_k)
            context = "\n\n".join(d["content"] for d in docs)

            if use_registry:
                rag_messages = prompt_registry.get("rag").format_messages(
                    context=context, question=question,
                )
            else:
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

    def invoke(self, message: str) -> str:
        """同步调用，自动加载历史、路由处理、保存交互。"""
        history = self._memory.load_history()
        messages = list(history)
        messages.append(HumanMessage(content=message))

        result = self._graph.invoke({"messages": messages, "intent": "", "context": ""})  # type: ignore[arg-type]
        ai_content = result["messages"][-1].content

        self._memory.save_interaction(
            HumanMessage(content=message),
            AIMessage(content=ai_content),
        )

        return ai_content

    def stream(self, message: str) -> Iterator[str]:
        """流式调用，逐 token 返回，结束后自动保存。"""
        history = self._memory.load_history()
        messages = list(history)
        messages.append(HumanMessage(content=message))

        seen_ids: set[str] = set()
        collected: list[str] = []
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
                collected.append(last.content)
                yield last.content

        if collected:
            full_response = "".join(collected)
            self._memory.save_interaction(
                HumanMessage(content=message),
                AIMessage(content=full_response),
            )

    def chat(self) -> None:
        """进入交互式多轮对话循环。"""
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
        """清除当前会话及所有记忆数据。"""
        self._memory.clear()

    def get_summary(self) -> Optional[str]:
        """获取当前会话的长期摘要。"""
        return self._memory.get_summary()

    def get_message_count(self) -> int:
        """获取当前会话的消息总数。"""
        return self._memory.get_message_count()

    @staticmethod
    def _get_default_model() -> str:
        from src.ai_chat.config import settings
        return settings.model_name


def _route_by_intent(state: UnifiedState) -> str:
    """条件路由 — 根据分类结果选择处理节点。"""
    return state.get("intent", "") or "react"
