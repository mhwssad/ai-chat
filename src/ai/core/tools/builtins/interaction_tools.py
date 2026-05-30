"""用户交互工具 — 向用户提问和发送消息。"""

import json
from collections.abc import Callable, Coroutine
from typing import Any

from langchain_core.tools import tool

from src.ai.core.tools.register import register_tool

# UI 层注册的交互回调
_interaction_handler: Callable[..., Coroutine[Any, Any, str]] | None = None


def set_interaction_handler(
    handler: Callable[..., Coroutine[Any, Any, str]] | None,
) -> None:
    """设置用户交互回调（由 UI 层调用）。"""
    global _interaction_handler
    _interaction_handler = handler


@tool
async def ask_user_question(question: str, options: list[str] | None = None) -> str:
    """向用户提问并等待回答。

    Args:
        question: 问题内容。
        options: 可选的选项列表（多选场景）。
    """
    if _interaction_handler is None:
        return json.dumps(
            {
                "status": "no_handler",
                "message": "未注册交互处理器，无法向用户提问",
                "question": question,
                "options": options,
            },
            ensure_ascii=False,
            indent=2,
        )

    payload: dict[str, Any] = {"type": "question", "question": question}
    if options:
        payload["options"] = options

    try:
        answer = await _interaction_handler(payload)
        return answer
    except Exception as exc:
        return f"交互失败: {exc}"


@tool
async def send_user_message(message: str) -> str:
    """向用户发送消息。

    Args:
        message: 消息内容。
    """
    if _interaction_handler is None:
        return json.dumps(
            {
                "status": "no_handler",
                "message": "未注册交互处理器，无法发送消息",
                "content": message,
            },
            ensure_ascii=False,
            indent=2,
        )

    try:
        result = await _interaction_handler({"type": "message", "content": message})
        return result or "已发送"
    except Exception as exc:
        return f"发送失败: {exc}"


# ── 自注册 ──────────────────────────────────────────────────────────────────

register_tool(ask_user_question, source_type="builtin")
register_tool(send_user_message, source_type="builtin")
