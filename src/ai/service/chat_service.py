"""统一对话服务 — 流式/非流式对话编排，含工具调用循环和记忆提取。

合并自：
- cli/chat_executor.py — 工具调用循环、记忆提取
- api/services/chat_service.py — 流式支持、多模态消息转换

共享服务层，CLI 和 API 统一使用。
"""

from __future__ import annotations

import json
from src.ai.config.logging_setup import get_logger
import uuid
from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.ai.core.context.types import ContextBuildRequest
from src.ai.service.types import ChatOptions, ChatResult

logger = get_logger(__name__)

# 工具结果最大字符数
_TOOL_RESULT_MAX_LEN = 2000


class ChatService:
    """统一对话服务。

    职责：
    1. 构建上下文（委托 ContextService）
    2. 调用 LLM + 工具调用循环
    3. 流式/非流式双模式
    4. 保存对话历史
    5. 可选记忆提取
    """

    def __init__(
        self,
        *,
        model_service: Any,
        context_service: Any,
        tool_manager: Any,
        memory_service: Any,
        chat_history_manager: Any,
        chat_llm: Any,
        thread_pool: Any,
    ) -> None:
        self._model_service = model_service
        self._context_service = context_service
        self._tool_manager = tool_manager
        self._memory_service = memory_service
        self._history_manager = chat_history_manager
        self._chat_llm = chat_llm
        self._thread_pool = thread_pool

    # ── 非流式入口 ────────────────────────────────────────────

    async def chat(
        self,
        user_input: str,
        session_id: str,
        *,
        options: ChatOptions | None = None,
    ) -> ChatResult:
        """非流式对话（含完整工具循环）。

        流程：
        1. 构建 ContextBuildRequest
        2. context_service.abuild() 构建上下文
        3. 绑定工具 -> LLM ainvoke
        4. 工具调用循环 (max_rounds)
        5. 保存历史
        6. 可选记忆提取

        Args:
            user_input: 用户输入文本。
            session_id: 会话 ID。
            options: 对话选项，None 使用默认值。

        Returns:
            ChatResult 包含 content, tool_calls, iterations 等。
        """
        opts = options or ChatOptions(session_id=session_id)
        if opts.session_id is None:
            opts.session_id = session_id

        try:
            # 1. 构建上下文
            request = ContextBuildRequest(
                messages=[HumanMessage(content=user_input)],
                session_id=session_id,
                enable_memory=opts.enable_memory,
                enable_tools=opts.enable_tools,
                enable_rag=opts.enable_rag,
            )
            context_result = await self._context_service.abuild(request)

            # 2. 获取 LLM（支持按请求参数覆盖）
            llm = self._get_llm(opts)

            # 3. 绑定工具
            tools = self._get_available_tools(opts.tools)
            llm_with_tools = llm.bind_tools(tools) if tools else llm

            # 4. 工具调用循环
            messages = list(context_result.messages)
            response, new_messages, iterations = await self._execute_tool_loop(
                llm_with_tools, messages, opts.max_rounds
            )

            # 5. 保存历史
            await self._save_history(session_id, user_input, response, new_messages)

            # 6. 可选记忆提取
            if opts.extract_memory:
                await self._extract_memory(session_id, user_input, response)

            content = (
                response.content if isinstance(response, AIMessage) else str(response)
            )
            return ChatResult(
                content=content or "",
                session_id=session_id,
                tool_calls=self._extract_tool_calls(response),
                iterations=iterations,
                context_sources=_context_sources_to_dict(context_result.source_summary),
            )

        except Exception as e:
            logger.error("对话执行异常: %s", e, exc_info=True)
            return ChatResult(
                content="",
                session_id=session_id,
                error=str(e),
            )

    # ── 流式入口 ──────────────────────────────────────────────

    async def chat_stream(
        self,
        user_input: str,
        session_id: str,
        *,
        options: ChatOptions | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """流式对话（SSE 事件流）。

        Yields:
            SSE 事件字典 {"event": str, "data": dict}。
            事件类型: token, tool_call, tool_result, done, error。
        """
        opts = options or ChatOptions(session_id=session_id, streaming=True)
        if opts.session_id is None:
            opts.session_id = session_id

        try:
            # 构建上下文
            request = ContextBuildRequest(
                messages=[HumanMessage(content=user_input)],
                session_id=session_id,
                enable_memory=opts.enable_memory,
                enable_tools=opts.enable_tools,
                enable_rag=opts.enable_rag,
            )
            context_result = await self._context_service.abuild(request)

            # 获取流式 LLM
            llm = self._get_llm(opts, streaming=True)

            # 绑定工具
            tools = self._get_available_tools(opts.tools)
            llm_with_tools = llm.bind_tools(tools) if tools else llm

            # 流式调用 LLM
            messages = list(context_result.messages)
            full_content, tool_calls = await self._stream_llm(llm_with_tools, messages)

            # 工具调用循环（流式模式下仍需执行）
            iterations = 0
            new_messages: list[AIMessage | ToolMessage] = []
            all_tool_calls: list[dict[str, Any]] = list(tool_calls)

            current_response = AIMessage(content=full_content, tool_calls=tool_calls)
            while tool_calls and iterations < opts.max_rounds:
                iterations += 1
                messages.append(current_response)
                new_messages.append(current_response)

                for tc in tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc["args"]
                    tool_id = tc["id"]

                    result_str = await self._execute_single_tool(
                        tool_name, tool_args, tool_id
                    )

                    yield {
                        "event": "tool_result",
                        "data": {
                            "name": tool_name,
                            "id": tool_id,
                            "result": result_str[:500],
                        },
                    }

                    tool_msg = ToolMessage(content=result_str, tool_call_id=tool_id)
                    messages.append(tool_msg)
                    new_messages.append(tool_msg)

                # 流式获取下一轮
                next_content, tool_calls = await self._stream_llm(
                    llm_with_tools, messages
                )
                all_tool_calls.extend(tool_calls)
                current_response = AIMessage(
                    content=next_content, tool_calls=tool_calls
                )

            # 保存历史
            final_content = (
                current_response.content
                if isinstance(current_response, AIMessage)
                else str(current_response)
            )
            await self._save_history(
                session_id, user_input, current_response, new_messages
            )

            # 可选记忆提取
            if opts.extract_memory:
                await self._extract_memory(session_id, user_input, current_response)

            # 完成事件
            yield {
                "event": "done",
                "data": {
                    "content": final_content or "",
                    "session_id": session_id,
                    "tool_calls": all_tool_calls,
                    "iterations": iterations,
                    "context_sources": _context_sources_to_dict(
                        context_result.source_summary
                    ),
                },
            }

        except Exception as e:
            logger.error("流式对话异常: %s", e, exc_info=True)
            yield {
                "event": "error",
                "data": {"error": str(e)},
            }

    # ── API 兼容入口 ──────────────────────────────────────────

    async def chat_with_messages(
        self,
        messages: list[dict[str, Any]],
        session_id: str | None = None,
        *,
        options: ChatOptions | None = None,
    ) -> ChatResult:
        """API 兼容入口 — 接收原始消息列表。

        从消息列表中提取最后一条用户消息，委托给 chat()。
        ContextService 通过 session_id 管理完整历史。

        Args:
            messages: 原始消息列表（dict 格式）。
            session_id: 会话 ID。
            options: 对话选项。

        Returns:
            ChatResult。
        """
        sid = session_id or str(uuid.uuid4())
        opts = options or ChatOptions(session_id=sid)

        # 提取最后一条用户消息
        user_input = ""
        for msg in reversed(messages):
            role = msg.get("role", "user")
            if role == "user":
                user_input = self._extract_text(msg.get("content", ""))
                break

        if not user_input:
            return ChatResult(
                content="",
                session_id=sid,
                error="没有找到用户消息",
            )

        return await self.chat(user_input, sid, options=opts)

    # ── 内部方法 ──────────────────────────────────────────────

    def _get_llm(self, options: ChatOptions, *, streaming: bool = False) -> Any:
        """获取 LLM 实例。

        如果 options 指定了 temperature 或 max_tokens，则按请求参数创建。
        否则使用容器预构建的 chat_llm。
        """
        if options.temperature is not None or options.max_tokens is not None:
            return self._model_service.get_chat_llm(
                temperature=options.temperature,
                max_tokens=options.max_tokens,
                streaming=streaming,
            )
        if streaming:
            return self._model_service.get_chat_llm(streaming=True)
        return self._chat_llm

    def _get_available_tools(self, tool_names: list[str] | None = None) -> list[Any]:
        """获取可用工具。

        Args:
            tool_names: 工具名称白名单，None 表示全部启用的工具。

        Returns:
            工具列表。
        """
        tools = self._tool_manager.list_tools(enabled_only=True)
        if tool_names is None:
            return tools
        return [t for t in tools if t.name in tool_names]

    async def _execute_tool_loop(
        self,
        llm_with_tools: Any,
        messages: list[Any],
        max_rounds: int,
    ) -> tuple[AIMessage, list[AIMessage | ToolMessage], int]:
        """执行工具调用循环。

        Args:
            llm_with_tools: 绑定了工具的 LLM 实例。
            messages: 消息列表（会被就地修改）。
            max_rounds: 最大循环轮数。

        Returns:
            (最终响应, 新消息列表, 循环轮数)
        """
        response: AIMessage = await llm_with_tools.ainvoke(messages)
        new_messages: list[AIMessage | ToolMessage] = []
        round_count = 0

        while response.tool_calls and round_count < max_rounds:
            round_count += 1
            messages.append(response)
            new_messages.append(response)

            for tc in response.tool_calls:
                result_str = await self._execute_single_tool(
                    tc["name"], tc["args"], tc["id"]
                )
                tool_msg = ToolMessage(content=result_str, tool_call_id=tc["id"])
                messages.append(tool_msg)
                new_messages.append(tool_msg)

            response = await llm_with_tools.ainvoke(messages)

        return response, new_messages, round_count

    async def _execute_single_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        tool_id: str,
    ) -> str:
        """执行单个工具调用并格式化结果。

        Args:
            tool_name: 工具名称。
            tool_args: 工具参数。
            tool_id: 工具调用 ID。

        Returns:
            格式化的结果字符串（已截断）。
        """
        try:
            tool_result = await self._tool_manager.execute(tool_name, tool_args)
            result_str = (
                tool_result
                if isinstance(tool_result, str)
                else json.dumps(tool_result, ensure_ascii=False, default=str)
            )
            if len(result_str) > _TOOL_RESULT_MAX_LEN:
                result_str = result_str[:_TOOL_RESULT_MAX_LEN] + "\n...(已截断)"
            return result_str
        except Exception as e:
            return f"工具执行失败: {e}"

    async def _stream_llm(
        self,
        llm: Any,
        messages: list[Any],
    ) -> tuple[str, list[dict[str, Any]]]:
        """流式调用 LLM，收集完整内容和工具调用。

        Args:
            llm: LLM 实例。
            messages: 消息列表。

        Returns:
            (完整内容, 工具调用列表)
        """
        full_content = ""
        tool_calls: list[dict[str, Any]] = []

        async for chunk in llm.astream(messages):
            if isinstance(chunk, AIMessage):
                if chunk.content:
                    full_content += str(chunk.content)
                if chunk.tool_calls:
                    tool_calls.extend(chunk.tool_calls)

        return full_content, tool_calls

    async def _save_history(
        self,
        session_id: str,
        user_input: str,
        response: AIMessage,
        new_messages: list[AIMessage | ToolMessage],
    ) -> None:
        """保存对话历史。

        Args:
            session_id: 会话 ID。
            user_input: 用户输入。
            response: 最终 AI 响应。
            new_messages: 工具循环中产生的新消息。
        """
        try:
            self._history_manager.add_message(
                session_id, HumanMessage(content=user_input)
            )
            for msg in new_messages:
                self._history_manager.add_message(session_id, msg)
            self._history_manager.add_message(session_id, response)
        except Exception:
            logger.debug("保存对话历史失败", exc_info=True)

    async def _extract_memory(
        self,
        session_id: str,
        user_input: str,
        response: AIMessage,
    ) -> None:
        """可选：从对话中提取记忆。

        Args:
            session_id: 会话 ID。
            user_input: 用户输入。
            response: AI 响应。
        """
        try:
            content = (
                response.content if isinstance(response, AIMessage) else str(response)
            )
            candidates = await self._memory_service.aextract_from_conversation(
                user_input, content
            )
            if candidates:
                await self._thread_pool.run_io(
                    self._memory_service.save_extracted,
                    candidates,
                    session_id=session_id,
                )
        except Exception:
            pass

    @staticmethod
    def _extract_tool_calls(response: AIMessage) -> list[dict[str, Any]]:
        """从响应中提取工具调用信息。"""
        if not isinstance(response, AIMessage) or not response.tool_calls:
            return []
        return [{"name": tc["name"], "args": tc["args"]} for tc in response.tool_calls]

    # ── 消息格式转换（API 兼容） ─────────────────────────────

    @staticmethod
    def convert_messages(messages: list[dict[str, Any]]) -> list[Any]:
        """转换消息格式为 LangChain 消息。

        支持多模态内容（文本 + 图像）。

        Args:
            messages: 原始消息列表。

        Returns:
            LangChain 消息列表。
        """
        lc_messages: list[Any] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                lc_messages.append(
                    SystemMessage(content=ChatService._extract_text(content))
                )
            elif role == "assistant":
                lc_messages.append(
                    AIMessage(content=ChatService._extract_text(content))
                )
            else:
                lc_messages.append(
                    HumanMessage(content=ChatService._convert_content(content))
                )
        return lc_messages

    @staticmethod
    def _extract_text(content: Any) -> str:
        """从内容中提取纯文本。"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(block.get("text", ""))
                elif hasattr(block, "type") and block.type == "text":
                    texts.append(block.text or "")
            return "\n".join(texts)
        return str(content)

    @staticmethod
    def _convert_content(content: Any) -> Any:
        """转换内容为 LangChain 格式（支持多模态）。"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            lc_content: list[dict[str, Any]] = []
            for block in content:
                if isinstance(block, dict):
                    block_type = block.get("type", "text")
                    if block_type == "text":
                        lc_content.append(
                            {"type": "text", "text": block.get("text", "")}
                        )
                    elif block_type == "image_url":
                        lc_content.append(
                            {
                                "type": "image_url",
                                "image_url": block.get("image_url", {}),
                            }
                        )
                elif hasattr(block, "type"):
                    if block.type == "text":
                        lc_content.append({"type": "text", "text": block.text or ""})
                    elif block.type == "image_url":
                        lc_content.append(
                            {
                                "type": "image_url",
                                "image_url": block.image_url or {},
                            }
                        )
            return lc_content
        return str(content)


def _context_sources_to_dict(sources: list[Any]) -> list[dict[str, Any]]:
    """转换上下文来源摘要为 API/TUI 可序列化结构。"""
    return [
        {
            "source": item.source,
            "item_count": item.item_count,
            "token_count": item.token_count,
            "truncated": item.truncated,
            "cacheable": item.cacheable,
            "summary": item.summary,
        }
        for item in sources
    ]
