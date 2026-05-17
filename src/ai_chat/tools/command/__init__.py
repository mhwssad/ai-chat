"""只读命令执行工具。"""

import json
import subprocess
from dataclasses import dataclass

from src.ai_chat.tools._helpers import resolve_project_path, is_within_project
from src.ai_chat.tools.registry import ToolType, registered_tool

_FORBIDDEN_TOKENS = (
    ";", "&&", "||", "|", ">", "<", "$(", "`",
)

# 单个输出流最大字符数
_MAX_OUTPUT_LENGTH = 10_000
_OUTPUT_TRUNCATION_NOTICE = "\n... [输出已截断，共 {total} 字符]"


@dataclass(frozen=True)
class _AllowedCommand:
    """白名单命令定义。"""

    prefix: str
    max_args: int = 0
    forbidden_arg_patterns: tuple[str, ...] = ()


_ALLOWED_COMMANDS = (
    _AllowedCommand("Get-Location"),
    _AllowedCommand("Get-ChildItem"),
    _AllowedCommand("dir"),
    _AllowedCommand("ls"),
    _AllowedCommand("type"),
    _AllowedCommand("cat"),
    _AllowedCommand("git status", max_args=0),
    _AllowedCommand(
        "git diff --stat",
        max_args=1,
        forbidden_arg_patterns=("/", "\\", ".."),
    ),
    _AllowedCommand("python --version", max_args=0),
)

_DANGEROUS_WORDS = (
    # 文件操作
    "remove-item", "del ", "rm ", "move-item", "copy-item",
    "set-content", "add-content", "out-file", "new-item",
    # 网络
    "invoke-webrequest", "invoke-restmethod", "curl ", "wget ",
    # 进程
    "start-process",
    # 包管理
    "pip install", "pip uninstall", "uv sync",
    "npm install", "npm run", "yarn ", "pnpm install", "conda install",
    # git 危险操作
    "git checkout", "git clean", "git reset",
    "git push", "git merge", "git rebase",
    # 系统
    "docker ", "chmod", "chown", "format-volume",
)


def _truncate(text: str) -> str:
    """截断过长输出，防止撑爆上下文窗口。"""
    if len(text) <= _MAX_OUTPUT_LENGTH:
        return text
    return text[:_MAX_OUTPUT_LENGTH] + _OUTPUT_TRUNCATION_NOTICE.format(total=len(text))


def _json_result(
    *,
    ok: bool,
    command: str,
    cwd: str,
    exit_code: int,
    stdout: str,
    stderr: str,
) -> str:
    return json.dumps(
        {
            "ok": ok,
            "command": command,
            "cwd": cwd,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
        },
        ensure_ascii=False,
        indent=2,
    )


def _is_safe_command(command: str) -> bool:
    normalized = command.strip()
    if not normalized:
        return False
    if any(token in normalized for token in _FORBIDDEN_TOKENS):
        return False
    lowered = normalized.lower()
    if any(word in lowered for word in _DANGEROUS_WORDS):
        return False
    for allowed in _ALLOWED_COMMANDS:
        if not normalized.startswith(allowed.prefix):
            continue
        remainder = normalized[len(allowed.prefix):].strip()
        if not remainder:
            return True
        args = remainder.split()
        if len(args) > allowed.max_args:
            return False
        if any(pat in remainder for pat in allowed.forbidden_arg_patterns):
            return False
        return True
    return False


@registered_tool(tool_type=ToolType.SYSTEM)
def run_command(command: str, cwd: str = ".", timeout: int = 10) -> str:
    """在项目目录内执行只读白名单命令，返回 JSON 字符串。"""
    resolved_cwd = resolve_project_path(cwd)
    if not is_within_project(resolved_cwd):
        return _json_result(
            ok=False,
            command=command,
            cwd=str(resolved_cwd),
            exit_code=1,
            stdout="",
            stderr="cwd 超出项目根目录",
        )

    if timeout <= 0 or timeout > 30:
        return _json_result(
            ok=False,
            command=command,
            cwd=str(resolved_cwd),
            exit_code=1,
            stdout="",
            stderr="timeout 必须在 1 到 30 秒之间",
        )

    if not _is_safe_command(command):
        return _json_result(
            ok=False,
            command=command,
            cwd=str(resolved_cwd),
            exit_code=1,
            stdout="",
            stderr="命令不在只读白名单内，或包含危险语法",
        )

    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                command,
            ],
            cwd=str(resolved_cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _json_result(
            ok=False,
            command=command,
            cwd=str(resolved_cwd),
            exit_code=124,
            stdout="",
            stderr="命令执行超时",
        )
    except OSError as e:
        return _json_result(
            ok=False,
            command=command,
            cwd=str(resolved_cwd),
            exit_code=1,
            stdout="",
            stderr=f"命令执行失败：{e}",
        )

    return _json_result(
        ok=completed.returncode == 0,
        command=command,
        cwd=str(resolved_cwd),
        exit_code=completed.returncode,
        stdout=_truncate(completed.stdout),
        stderr=_truncate(completed.stderr),
    )
