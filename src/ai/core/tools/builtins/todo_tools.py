"""待办事项工具。"""

import json
from typing import Any

from langchain_core.tools import tool

from src.ai.core.tools.registry import register_tool

_todos: list[dict[str, Any]] = []


@tool
async def todo_write(todos: list[dict[str, Any]]) -> str:
    """管理待办事项列表。

    Args:
        todos: 待办事项列表，每项为包含 content/status 等字段的字典。
    """
    global _todos
    _todos = [dict(item) if isinstance(item, dict) else {"content": str(item)} for item in todos]
    return json.dumps(_todos, ensure_ascii=False, indent=2)


# ── 自注册 ──────────────────────────────────────────────────────────────────

register_tool(todo_write, source_type="builtin")
