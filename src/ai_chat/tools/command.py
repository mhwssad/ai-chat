"""只读命令执行工具。"""

import json
import subprocess
from pathlib import Path

from src.ai_chat.tools.registry import ToolType, registered_tool

project_root = Path(__file__).resolve().parents[3]

_FORBIDDEN_TOKENS = (
    ";", "&&", "||", "|", ">", "<", "$(", "`",
)
_ALLOWED_PREFIXES = (
    "Get-Location",
    "Get-ChildItem",
    "dir",
    "ls",
    "type",
    "cat",
    "git status",
    "git diff --stat",
    "python --version",
)


def _resolve_cwd(raw_cwd: str) -> Path:
    path = Path(raw_cwd)
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


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
    dangerous_words = (
        "remove-item", "del ", "rm ", "move-item", "copy-item",
        "set-content", "add-content", "out-file", "invoke-webrequest",
        "start-process", "pip install", "uv sync", "git checkout",
        "git clean", "git reset", "new-item",
    )
    if any(word in lowered for word in dangerous_words):
        return False
    return any(normalized.startswith(prefix) for prefix in _ALLOWED_PREFIXES)


@registered_tool(tool_type=ToolType.SYSTEM)
def run_command(command: str, cwd: str = ".", timeout: int = 10) -> str:
    """在项目目录内执行只读白名单命令，返回 JSON 字符串。"""
    resolved_cwd = _resolve_cwd(cwd)
    try:
        resolved_cwd.relative_to(project_root)
    except ValueError:
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
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
