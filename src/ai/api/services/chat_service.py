"""对话服务 — 流式/非流式对话编排。"""

from __future__ import annotations

import logging
import uuid
from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.ai.core.context.types import ContextBuildRequest

logger = logging.getLogger(__name__)


class ChatService:
    """对话服务。

    职责：
    1. 构建上下文
    2. 调用 LLM
    3. 处理工具调用
    4. 返回结果（流式/非流式）
    """

    def __init__(
        self,
        *,
        model_service: Any,
        context_service: Any,
        tool_manager: Any,
    ) -> None:
        self._model = model_service
        self._context = context_service
        self._tools = tool_manager

    async def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        session_id: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[str] | None = None,
    ) -> dict[str, Any]:
        """非流式对话。

        Args:
            messages: 消息列表。
            session_id: 会话 ID。
            temperature: 温度参数。
            max_tokens: 最大输出 token 数。
            tools: 可用工具列表。

        Returns:
            对话响应。
        """
        session_id = session_id or str(uuid.uuid4())

        # 转换消息格式
        lc_messages = self._convert_messages(messages)

        # 构建上下文
        request = ContextBuildRequest(
            session_id=session_id,
            messages=lc_messages,
        )
        context_result = await self._context.abuild(request)

        # 获取 LLM
        llm = self._model.get_chat_llm(
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=False,
        )

        # 绑定工具
        available_tools = self._get_available_tools(tools)
        if available_tools:
            llm = llm.bind_tools(available_tools)

        # 调用 LLM
        response = await llm.ainvoke(context_result.messages)

        # 处理响应
        if isinstance(response, AIMessage):
            content = response.content or ""
            tool_calls = [
                {
                    "id": tc.get("id", ""),
                    "name": tc.get("name", ""),
                    "args": tc.get("args", {}),
                }
                for tc in (response.tool_calls or [])
            ]
        else:
            content = str(response)
            tool_calls = []

        # 添加消息到历史
        last_content = messages[-1].get("content", "") if messages else ""
        last_text = self._extract_text(last_content)
        await self._context.strategy.aadd_message(
            session_id, HumanMessage(content=last_text)
        )
        await self._context.strategy.aadd_message(
            session_id, AIMessage(content=str(content))
        )

        return {
            "content": content,
            "session_id": session_id,
            "tool_calls": tool_calls,
            "usage": {},
        }

    async def chat_stream(
        self,
        *,
        messages: list[dict[str, Any]],
        session_id: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """流式对话（SSE）。

        Args:
            messages: 消息列表。
            session_id: 会话 ID。
            temperature: 温度参数。
            max_tokens: 最大输出 token 数。
            tools: 可用工具列表。

        Yields:
            SSE 事件。
        """
        session_id = session_id or str(uuid.uuid4())

        # 转换消息格式
        lc_messages = self._convert_messages(messages)

        # 构建上下文
        request = ContextBuildRequest(
            session_id=session_id,
            messages=lc_messages,
        )
        context_result = await self._context.abuild(request)

        # 获取流式 LLM
        llm = self._model.get_chat_llm(
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True,
        )

        # 绑定工具
        available_tools = self._get_available_tools(tools)
        if available_tools:
            llm = llm.bind_tools(available_tools)

        # 流式调用 LLM
        full_content = ""
        tool_calls = []

        async for chunk in llm.astream(context_result.messages):
            if isinstance(chunk, AIMessage):
                if chunk.content:
                    full_content += str(chunk.content)
                    yield {
                        "event": "token",
                        "data": {"content": chunk.content},
                    }
                if chunk.tool_calls:
                    tool_calls.extend(chunk.tool_calls)
                    yield {
                        "event": "tool_call",
                        "data": {"tool_calls": chunk.tool_calls},
                    }

        # 添加消息到历史
        last_content = messages[-1].get("content", "") if messages else ""
        last_text = self._extract_text(last_content)
        await self._context.strategy.aadd_message(
            session_id, HumanMessage(content=last_text)
        )
        await self._context.strategy.aadd_message(
            session_id, AIMessage(content=full_content)
        )

        # 完成事件
        yield {
            "event": "done",
            "data": {
                "content": full_content,
                "session_id": session_id,
                "tool_calls": tool_calls,
            },
        }

    def _convert_messages(self, messages: list[dict[str, Any]]) -> list[Any]:
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
                lc_messages.append(SystemMessage(content=self._extract_text(content)))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=self._extract_text(content)))
            else:
                # 用户消息支持多模态
                lc_messages.append(HumanMessage(content=self._convert_content(content)))
        return lc_messages

    @staticmethod
    def _extract_text(content: Any) -> str:
        """从内容中提取纯文本。"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = []
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
            lc_content = []
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
                            {"type": "image_url", "image_url": block.image_url or {}}
                        )
            return lc_content
        return str(content)

    def _get_available_tools(
        self, tool_names: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """获取可用工具 schema。

        Args:
            tool_names: 工具名称列表，None 表示全部。

        Returns:
            工具 schema 列表。
        """
        all_schemas = self._tools.list_schemas(enabled_only=True)

        if tool_names is None:
            return all_schemas

        # 过滤指定工具
        return [s for s in all_schemas if s["function"]["name"] in tool_names]
