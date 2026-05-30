"""计划模式工具 — 进入和退出计划模式。"""

import json
from typing import Any

from langchain_core.tools import tool

from src.ai.core.tools.register import register_tool

_plan_state: dict[str, Any] = {"active": False, "plan": None}


def get_plan_state() -> dict[str, Any]:
    """获取当前计划模式状态（供外部查询）。"""
    return dict(_plan_state)


@tool
async def enter_plan_mode(goal: str = "") -> str:
    """进入计划模式，开始制定实现计划。

    Args:
        goal: 计划目标描述。
    """
    _plan_state["active"] = True
    _plan_state["plan"] = None
    return json.dumps(
        {
            "status": "entered",
            "goal": goal,
            "message": "已进入计划模式。请制定实现计划，完成后调用 exit_plan_mode 提交。",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def exit_plan_mode(plan: str) -> str:
    """提交计划等待审批并退出计划模式。

    Args:
        plan: 完整的计划内容。
    """
    _plan_state["active"] = False
    _plan_state["plan"] = plan
    return json.dumps(
        {
            "status": "submitted",
            "plan_length": len(plan),
            "message": "计划已提交，等待用户审批。",
        },
        ensure_ascii=False,
        indent=2,
    )


# ── 自注册 ──────────────────────────────────────────────────────────────────

register_tool(enter_plan_mode, source_type="builtin")
register_tool(exit_plan_mode, source_type="builtin")
