"""内置记忆的对话智能体 — 开箱即用的多轮对话 Agent。"""

from typing import Iterator, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain.agents import create_agent

from src.ai_chat.llm import llm_factory
from src.ai_chat.memory import ConversationMemory, MemoryConfig
from src.ai_chat.tools.registry import tool_registry


class MemoryAgent:
    """自带记忆的 ReAct Agent。

    内部自动创建 ConversationMemory，无需调用方管理记忆。
    支持恢复历史会话（传入 session_id）或创建新会话。

    Usage::

        agent = MemoryAgent(model_name="qwen-turbo")
        agent.chat()  # 进入交互式多轮对话

        # 或者手动调用
        response = agent.invoke("你好")
        response = agent.invoke("我刚才说了什么")  # 能回忆上文
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[list] = None,
        session_id: Optional[str] = None,
        memory_config: Optional[MemoryConfig] = None,
    ) -> None:
        self._model_name = model_name or self._get_default_model()
        self._system_prompt = system_prompt or "你是一个有帮助的 AI 助手。请用中文回答用户的问题。你可以使用工具来完成任务。"
        self._tools = tools or tool_registry.get_all()

        provider = llm_factory.get_chat_provider(self._model_name)
        self._llm = provider.get_client(self._model_name)

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

    def invoke(self, message: str) -> str:
        """同步调用，自动加载历史并保存交互。"""
        history = self._memory.load_history()
        messages = list(history)
        messages.append(HumanMessage(content=message))

        result = self._agent.invoke({"messages": messages})  # type: ignore[arg-type]
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

        collected: list[str] = []
        for event in self._agent.stream({"messages": messages}, stream_mode="values"):  # type: ignore[arg-type]
            if not event.get("messages"):
                continue
            last = event["messages"][-1]
            if isinstance(last, AIMessage) and isinstance(last.content, str) and last.content:
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
