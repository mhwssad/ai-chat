"""Skill 指令模板渲染 — $ARGUMENTS 替换、!`command` 动态执行。"""

import logging
import os
import re
import shlex
import subprocess

logger = logging.getLogger(__name__)

# 安全命令白名单 — 仅允许执行这些命令
_SAFE_COMMANDS: set[str] = {
    # 文件系统只读操作
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "file",
    "stat",
    "du",
    "df",
    "find",
    "tree",
    "realpath",
    "basename",
    "dirname",
    # 文本处理
    "grep",
    "awk",
    "sed",
    "sort",
    "uniq",
    "cut",
    "tr",
    "tee",
    "xargs",
    "jq",
    "yq",
    # 版本控制
    "git",
    "gh",
    # 包管理与构建
    "npm",
    "yarn",
    "pnpm",
    "bun",
    "node",
    "npx",
    "pip",
    "uv",
    "python",
    "python3",
    "cargo",
    "rustc",
    "go",
    "make",
    "cmake",
    # 系统信息
    "echo",
    "printf",
    "date",
    "whoami",
    "hostname",
    "uname",
    "env",
    "printenv",
    # 网络（只读）
    "curl",
    "wget",
    "ping",
}


class SkillRenderer:
    """渲染 Skill 指令模板。"""

    def __init__(self, *, allowed_commands: set[str] | None = None) -> None:
        """初始化渲染器。

        Args:
            allowed_commands: 自定义允许的命令集合，默认使用内置白名单。
        """
        self._allowed_commands = allowed_commands or _SAFE_COMMANDS

    def render(self, template: str, *, arguments: str = "") -> str:
        """渲染模板：$ARGUMENTS 替换 → !`command` 执行。

        Args:
            template: SKILL.md 正文模板。
            arguments: 用户输入的完整参数字符串（/command 后面的内容）。

        Returns:
            渲染后的字符串。
        """
        result = self._substitute_arguments(template, arguments)
        result = self._execute_commands(result)
        return result

    @staticmethod
    def _substitute_arguments(template: str, arguments: str) -> str:
        """替换 $ARGUMENTS[n]、$ARGUMENTS、$0、$1... 占位符。"""
        parts = arguments.split()

        # 先替换 $ARGUMENTS[n]（更具体的模式优先）
        def _replace_indexed(match: re.Match) -> str:
            idx = int(match.group(1))
            return parts[idx] if idx < len(parts) else ""

        result = re.sub(r"\$ARGUMENTS\[(\d+)\]", _replace_indexed, template)

        # 再替换 $ARGUMENTS（完整参数）
        result = result.replace("$ARGUMENTS", arguments)

        # 最后替换 $0、$1、$2...（位置参数，倒序避免 $1 先匹配 $10）
        for i in range(len(parts) - 1, -1, -1):
            result = result.replace(f"${i}", parts[i])

        return result

    def _execute_commands(self, template: str) -> str:
        """执行 !`command` 动态命令并替换为 stdout。

        使用 shlex.split() + shell=False 防止 Shell 注入，
        并通过白名单限制可执行的命令。
        """

        def _run(match: re.Match) -> str:
            cmd_str = match.group(1)

            # 使用 shlex.split 解析命令，防止注入
            try:
                cmd_parts = shlex.split(cmd_str)
            except ValueError as exc:
                logger.warning("命令解析失败: %s — %s", cmd_str, exc)
                return f"[命令解析失败: {exc}]"

            if not cmd_parts:
                return "[空命令]"

            # 检查命令是否在白名单中
            cmd_name = os.path.basename(cmd_parts[0])
            if cmd_name not in self._allowed_commands:
                logger.warning("命令不在白名单中: %s", cmd_name)
                return f"[命令被拒绝: {cmd_name} 不在允许列表中]"

            try:
                proc = subprocess.run(
                    cmd_parts,
                    shell=False,  # 关键：禁用 shell 解释
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return proc.stdout.strip()
            except subprocess.TimeoutExpired:
                logger.warning("动态命令超时: %s", cmd_str)
                return f"[命令超时: {cmd_str}]"
            except Exception as exc:
                logger.warning("动态命令执行失败: %s — %s", cmd_str, exc)
                return f"[命令失败: {exc}]"

        return re.sub(r"!`([^`]+)`", _run, template)
