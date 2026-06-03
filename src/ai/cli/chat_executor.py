"""对话执行逻辑 — 从 Dashboard 提取的 LLM + 工具循环。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

logger = logging.getLogger(__name__)


@dataclass
class ChatResult:
    """对话执行结果。"""

    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    iterations: int = 0


class ChatExecutor:
    """对话执行器。

    封装 LLM + 工具循环逻辑，从 Dashboard._do_chat() 提取。

    Args:
        container: DI 容器实例。
    """

    def __init__(self, container: Any) -> None:
        self._container = container

    async def execute(
        self,
        user_input: str,
        session_id: str,
        *,
        max_rounds: int = 10,
    ) -> ChatResult:
        """执行单轮对话。

        Args:
            user_input: 用户输入。
            session_id: 会话 ID。
            max_rounds: 最大工具调用轮数。

        Returns:
            对话执行结果。
        """
        memory_svc = self._container.memory_container.memory_service()
        context_svc = self._container.context_container.context_service()
        chat_llm = self._container.chat_llm()
        chat_cfg = self._container.chat_model_config()
        tool_mgr = self._container.tool_container.tool_manager()

        tools = tool_mgr.list_tools(enabled_only=True)

        from src.ai.core.context import ContextBuildRequest

        # 构建上下文
        request = ContextBuildRequest(
            messages=[HumanMessage(content=user_input)],
            model_config=chat_cfg,
            session_id=session_id,
            enable_memory=True,
            enable_tools=True,
            enable_rag=False,
        )
        result = await context_svc.abuild(request)

        # 绑定工具并调用 LLM
        llm_with_tools = chat_llm.bind_tools(tools)
        response: AIMessage = await llm_with_tools.ainvoke(result.messages)

        # 工具调用循环
        messages = list(result.messages)
        new_messages: list[AIMessage | ToolMessage] = []
        round_count = 0

        while response.tool_calls and round_count < max_rounds:
            round_count += 1
            messages.append(response)
            new_messages.append(response)

            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["args"]
                tool_id = tc["id"]

                try:
                    tool_result = await tool_mgr.execute(tool_name, tool_args)
                    result_str = (
                        tool_result
                        if isinstance(tool_result, str)
                        else json.dumps(tool_result, ensure_ascii=False, default=str)
                    )
                    if len(result_str) > 2000:
                        result_str = result_str[:2000] + "\n...(已截断)"
                except Exception as e:
                    result_str = f"工具执行失败: {e}"

                tool_msg = ToolMessage(content=result_str, tool_call_id=tool_id)
                messages.append(tool_msg)
                new_messages.append(tool_msg)

            response = await llm_with_tools.ainvoke(messages)

        # 保存历史
        history_mgr = self._container.context_container.chat_history_manager()
        history_mgr.add_message(session_id, HumanMessage(content=user_input))
        for msg in new_messages:
            history_mgr.add_message(session_id, msg)
        history_mgr.add_message(session_id, response)

        # 提取记忆
        try:
            candidates = await memory_svc.aextract_from_conversation(
                user_input, response.content
            )
            if candidates:
                memory_svc.save_extracted(candidates, session_id=session_id)
        except Exception:
            pass

        return ChatResult(
            content=response.content,  # type: ignore[arg-type]
            tool_calls=[
                {"name": tc["name"], "args": tc["args"]}
                for tc in (response.tool_calls or [])
            ],
            iterations=round_count,
        )
