"""Shell 命令工具。"""

import asyncio
import subprocess

from langchain_core.tools import tool

from src.ai.core.tools.register import register_tool


@tool
async def bash(command: str, timeout: float = 120) -> str:
    """执行 shell 命令并返回输出。

    Args:
        command: 要执行的命令。
        timeout: 超时秒数。
    """
    completed = await asyncio.to_thread(
        subprocess.run,
        command,
        capture_output=True,
        text=True,
        shell=True,
        timeout=timeout,
    )
    output = completed.stdout
    if completed.returncode != 0:
        output += f"\n[stderr]\n{completed.stderr}"
    return output or f"(退出码: {completed.returncode})"


@tool
async def sleep(seconds: float = 1) -> str:
    """等待指定时间。

    Args:
        seconds: 等待秒数。
    """
    await asyncio.sleep(seconds)
    return f"已等待 {seconds} 秒"


# ── 自注册 ──────────────────────────────────────────────────────────────────

register_tool(bash, source_type="builtin", permissions=["command_exec"], essential=True)
register_tool(sleep, source_type="builtin")
