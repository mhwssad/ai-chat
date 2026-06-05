"""超时 ToolNode — 替代 LangGraph 预置 ToolNode，支持工具级超时。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode

from src.ai.exception.tool_exception import ToolConfirmationRequiredError

logger = logging.getLogger(__name__)


class TimeoutToolNode(ToolNode):
    """带超时的 ToolNode。

    继承 LangGraph ToolNode，在每个工具调用上包装 asyncio.wait_for()。
    超时时返回错误消息而非抛出异常，让 LLM 有机会处理超时情况。

    Args:
        tools: 工具列表。
        default_timeout: 默认超时秒数（默认 120）。
        handle_tool_errors: 是否捕获工具异常（默认 True）。
        **kwargs: 传递给 ToolNode 的其他参数。
    """

    def __init__(
        self,
        tools: list,
        *,
        default_timeout: float = 120.0,
        handle_tool_errors: bool = True,
        tool_manager: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(tools, handle_tool_errors=handle_tool_errors, **kwargs)
        self._default_timeout = default_timeout
        self._tool_manager = tool_manager

    async def _arun_one(  # type: ignore[override]
        self,
        call: dict[str, Any],
        input_type: str,
        config: Any,
    ) -> ToolMessage:
        """执行单个工具调用，带超时包装。

        Args:
            call: 工具调用信息（name, args, id）。
            input_type: 输入类型。
            config: LangChain 配置。

        Returns:
            工具执行结果消息。
        """
        name = call.get("name", "")
        call_id = call.get("id", "")
        arguments = call.get("args", {}) or {}

        try:
            if self._tool_manager is not None:
                result = await self._tool_manager.execute(
                    name,
                    arguments,
                    config=config,
                    timeout=self._default_timeout,
                )
                content = result if isinstance(result, str) else str(result)
                return ToolMessage(content=content, tool_call_id=call_id, name=name)

            return await asyncio.wait_for(
                super()._arun_one(call, input_type, config),  # type: ignore[arg-type]
                timeout=self._default_timeout,
            )  # type: ignore[return-value]
        except TimeoutError:
            logger.warning("工具 %s 执行超时 (%.1fs)", name, self._default_timeout)
            return ToolMessage(
                content=f"Error: 工具 {name} 执行超时 ({self._default_timeout}s)",
                tool_call_id=call_id,
                name=name,
            )
        except ToolConfirmationRequiredError as exc:
            logger.info("工具 %s 等待用户确认", name)
            return ToolMessage(
                content=f"ConfirmationRequired: {exc}",
                tool_call_id=call_id,
                name=name,
            )
        except Exception as e:
            # 其他异常由父类 handle_tool_errors 处理
            if not self.handle_tool_errors:  # type: ignore[attr-defined]
                raise
            logger.error("工具 %s 执行异常: %s", name, str(e), exc_info=True)
            return ToolMessage(
                content=f"Error: {e}",
                tool_call_id=call_id,
                name=name,
            )

    async def ainvoke(
        self,
        input: dict[str, Any] | Any,
        config: Any = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """异步执行所有工具调用（带超时）。

        Args:
            input: 输入状态（包含 messages）。
            config: LangChain 配置。
            **kwargs: 其他参数。

        Returns:
            包含 ToolMessage 列表的状态更新。
        """
        # 提取工具调用
        message = input.get("messages", [])[-1] if isinstance(input, dict) else input
        if not isinstance(message, AIMessage) or not message.tool_calls:
            return {"messages": []}

        input_type = "list" if isinstance(input, list) else "dict"

        # 并行执行所有工具调用
        tasks = [
            self._arun_one(call, input_type, config)  # type: ignore[arg-type]
            for call in message.tool_calls
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        messages: list[ToolMessage] = []
        user_approval_pending = False
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                call = message.tool_calls[i]
                logger.error(
                    "工具 %s gather 异常: %s", call.get("name", ""), str(result)
                )
                messages.append(
                    ToolMessage(
                        content=f"Error: {result}",
                        tool_call_id=call.get("id", ""),
                        name=call.get("name", ""),
                    )
                )
            else:
                if isinstance(result.content, str) and result.content.startswith(
                    "ConfirmationRequired:"
                ):
                    user_approval_pending = True
                messages.append(result)  # type: ignore[arg-type]

        return {
            "messages": messages,
            "user_approval_pending": user_approval_pending,
        }
