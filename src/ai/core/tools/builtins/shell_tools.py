"""Shell 命令工具。"""

import asyncio
import logging
import re
import subprocess

from langchain_core.tools import tool

from src.ai.core.tools.register import register_tool

logger = logging.getLogger(__name__)

# 危险命令黑名单 — 阻止破坏性操作
_BLOCKED_COMMANDS = frozenset(
    {
        "rm",
        "rmdir",
        "del",
        "format",
        "mkfs",
        "dd",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
        "chmod",
        "chown",
        "chgrp",
        "passwd",
        "useradd",
        "userdel",
        "usermod",
        "groupadd",
        "groupdel",
        "groupmod",
        "iptables",
        "ufw",
        "firewall-cmd",
        "systemctl",
        "service",
        "kill",
        "killall",
        "pkill",
        "mv",
        "cp",
        "scp",
        "rsync",
    }
)

# 危险模式 — 阻止命令注入
_DANGEROUS_PATTERNS = [
    r";\s*rm\b",  # ; rm
    r"\|\s*rm\b",  # | rm
    r"&&\s*rm\b",  # && rm
    r">\s*/dev/",  # > /dev/*
    r"mkfifo",  # 创建命名管道
    r"nc\s+-l",  # netcat 监听
    r"python\s+-c.*import\s+os",  # python -c "import os"
    r"bash\s+-i",  # 交互式 bash
    r"/dev/tcp/",  # bash 反弹 shell
    r"curl.*\|\s*sh",  # curl | sh
    r"wget.*\|\s*sh",  # wget | sh
]


def _validate_command(command: str) -> None:
    """验证命令安全性。

    Args:
        command: 待验证的命令。

    Raises:
        ValueError: 命令不安全。
    """
    # 检查危险模式
    for pattern in _DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            raise ValueError(f"命令包含危险模式: {pattern}")

    # 提取命令名（取第一个非空格词）
    parts = command.strip().split()
    if not parts:
        raise ValueError("空命令")

    cmd_name = parts[0].split("/")[-1]  # 处理 /bin/rm 等路径
    if cmd_name in _BLOCKED_COMMANDS:
        raise ValueError(f"命令被阻止: {cmd_name}")


@tool
async def bash(command: str, timeout: float = 120) -> str:
    """执行 shell 命令并返回输出。

    Args:
        command: 要执行的命令。
        timeout: 超时秒数。
    """
    # 安全验证
    _validate_command(command)

    logger.info("执行命令: %s", command[:100])

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
