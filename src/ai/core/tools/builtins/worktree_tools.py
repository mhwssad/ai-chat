"""Git Worktree 管理工具。"""

import json
import subprocess

from langchain_core.tools import tool

from src.ai.core.tools.register import register_tool
from src.ai.utils.thread_pool import get_thread_pool

_current_worktree: str | None = None


@tool
async def enter_worktree(name: str = "", branch: str = "") -> str:
    """创建并进入 git worktree。

    Args:
        name: worktree 名称（同时用作新分支名）。
        branch: 使用已有分支创建 worktree（与 name 二选一）。
    """
    global _current_worktree

    if _current_worktree:
        return f"错误: 已有活跃 worktree {_current_worktree}，请先 exit_worktree"

    if not name and not branch:
        return "错误: 必须指定 name 或 branch"

    worktree_path = f".claude/worktrees/{name or branch}"

    if branch:
        cmd = f"git worktree add {worktree_path} {branch}"
    else:
        cmd = f"git worktree add {worktree_path} -b {name}"

    def _run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(cmd, capture_output=True, text=True, shell=True)

    result = await get_thread_pool().run_io(_run)
    if result.returncode != 0:
        return f"创建 worktree 失败:\n{result.stderr}"

    _current_worktree = worktree_path
    return json.dumps(
        {
            "status": "ok",
            "worktree": worktree_path,
            "branch": branch or name,
            "command": cmd,
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def exit_worktree(action: str = "keep") -> str:
    """退出当前 git worktree。

    Args:
        action: keep（保留）或 remove（删除 worktree 及其分支）。
    """
    global _current_worktree

    if not _current_worktree:
        return "错误: 当前没有活跃的 worktree"

    path = _current_worktree

    if action == "remove":
        cmd = f"git worktree remove {path} --force"

        def _run() -> subprocess.CompletedProcess[str]:
            return subprocess.run(cmd, capture_output=True, text=True, shell=True)

        result = await get_thread_pool().run_io(_run)
        if result.returncode != 0:
            return f"删除 worktree 失败:\n{result.stderr}"
        _current_worktree = None
        return json.dumps({"status": "removed", "worktree": path}, ensure_ascii=False)

    _current_worktree = None
    return json.dumps(
        {"status": "exited", "worktree": path, "action": "keep"}, ensure_ascii=False
    )


# ── 自注册 ──────────────────────────────────────────────────────────────────

register_tool(enter_worktree, source_type="builtin", permissions=["command_exec"])
register_tool(exit_worktree, source_type="builtin", permissions=["command_exec"])
