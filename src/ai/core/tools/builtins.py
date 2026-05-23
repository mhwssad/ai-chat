"""内置工具定义。"""

from __future__ import annotations

import asyncio
import glob as glob_lib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .errors import ToolExecutionError
from .types import ToolCallRequest, ToolCallResult, ToolDefinition

_todos: list[dict[str, Any]] = []


def get_builtin_tools() -> list[ToolDefinition]:
    """返回 MVP 内置工具列表。"""
    return [
        _tool("save_file", "读取本地文件内容", _file_read, ["file_read"], _file_read_schema()),
        _tool("file_read", "读取本地文件内容", _file_read, ["file_read"], _file_read_schema()),
        _tool("edit_file", "对文件进行字符串替换", _file_edit, ["file_read", "file_write"], _file_edit_schema()),
        _tool("file_write", "创建或覆盖文件", _file_write, ["file_write"], _file_write_schema()),
        _tool("Write", "创建或覆盖文件", _file_write, ["file_write"], _file_write_schema()),
        _tool("Glob", "按 glob 模式搜索文件", _glob, ["file_read"], _glob_schema()),
        _tool("Grep", "使用正则表达式搜索文件内容", _grep, ["file_read"], _grep_schema()),
        _tool("Bash", "执行 shell 命令并返回输出", _bash, ["command_exec"], _bash_schema(), timeout=120),
        _tool("Sleep", "等待指定时间", _sleep, [], _sleep_schema()),
        _tool("TodoWrite", "管理待办事项列表", _todo_write, [], _todo_schema()),
        _tool("ListMcpResources", "列出 MCP 服务器可用资源", _list_mcp_resources, ["external_service"], _mcp_resource_list_schema()),
        _tool("ReadMcpResource", "从 MCP 服务器读取资源", _read_mcp_resource, ["external_service"], _mcp_resource_read_schema()),
        *get_placeholder_tools(),
    ]


def get_placeholder_tools() -> list[ToolDefinition]:
    """暂未实现但可被发现的工具声明。"""
    placeholders = {
        "NotebookEdit": "编辑 Jupyter 笔记本单元格",
        "WebSearch": "搜索网络获取最新信息",
        "WebFetch": "获取网页内容并提取信息",
        "TaskCreate": "创建新任务",
        "TaskGet": "获取任务详情",
        "TaskList": "列出所有任务",
        "TaskUpdate": "更新任务状态",
        "TaskStop": "停止运行中的后台任务",
        "TaskOutput": "获取任务执行输出",
        "Agent": "分叉子代理并行处理复杂任务",
        "Skill": "执行 slash 命令技能",
        "EnterPlanMode": "进入计划模式",
        "ExitPlanMode": "提交计划等待审批",
        "EnterWorktree": "创建 git worktree",
        "ExitWorktree": "退出 worktree",
        "AskUserQuestion": "向用户提问",
        "SendUserMessage": "向用户发送消息",
        "CronCreate": "创建定时任务",
        "CronDelete": "删除定时任务",
        "CronList": "列出所有定时任务",
        "RemoteTrigger": "管理远程代理触发器",
        "TeamCreate": "创建团队协调多代理工作",
        "TeamDelete": "删除团队及任务目录",
        "LSP": "代码智能",
        "SendMessage": "向子代理发送消息",
        "ToolSearchTool": "获取延迟工具 schema",
    }
    return [
        ToolDefinition(
            name=name,
            description=description,
            enabled=False,
            status="registered",
            input_schema={"type": "object", "properties": {}},
            metadata={"placeholder": True},
        )
        for name, description in placeholders.items()
    ]


def _tool(
    name: str,
    description: str,
    handler,
    permissions: list[str],
    input_schema: dict[str, Any],
    *,
    timeout: float | None = None,
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=description,
        input_schema=input_schema,
        permissions=permissions,
        timeout_seconds=timeout,
        handler=handler,
    )


async def _file_read(request: ToolCallRequest) -> ToolCallResult:
    path = Path(str(request.arguments["path"]))
    max_bytes = int(request.arguments.get("max_bytes") or 1024 * 1024)
    data = await asyncio.to_thread(path.read_bytes)
    truncated = len(data) > max_bytes
    data = data[:max_bytes]
    try:
        content: Any = data.decode(request.arguments.get("encoding") or "utf-8")
        content_type = "text"
    except UnicodeDecodeError:
        content = data.hex()
        content_type = "binary_hex"
    return ToolCallResult(
        tool_name=request.tool_name,
        content=content,
        structured_content={
            "path": str(path),
            "content_type": content_type,
            "bytes": len(data),
            "truncated": truncated,
        },
    )


async def _file_write(request: ToolCallRequest) -> ToolCallResult:
    path = Path(str(request.arguments["path"]))
    content = str(request.arguments.get("content") or "")
    path.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(path.write_text, content, request.arguments.get("encoding") or "utf-8")
    return ToolCallResult(
        tool_name=request.tool_name,
        content=f"written: {path}",
        structured_content={"path": str(path), "bytes": len(content.encode("utf-8"))},
    )


async def _file_edit(request: ToolCallRequest) -> ToolCallResult:
    path = Path(str(request.arguments["path"]))
    old = str(request.arguments["old"])
    new = str(request.arguments["new"])
    text = await asyncio.to_thread(path.read_text, request.arguments.get("encoding") or "utf-8")
    count = int(request.arguments.get("count") or 1)
    if old not in text:
        raise ToolExecutionError("待替换内容不存在", context={"path": str(path)})
    updated = text.replace(old, new, count)
    await asyncio.to_thread(path.write_text, updated, request.arguments.get("encoding") or "utf-8")
    return ToolCallResult(
        tool_name=request.tool_name,
        content=f"edited: {path}",
        structured_content={"path": str(path), "replacements": text.count(old) if count < 0 else min(text.count(old), count)},
    )


async def _glob(request: ToolCallRequest) -> ToolCallResult:
    pattern = str(request.arguments["pattern"])
    root = Path(str(request.arguments.get("root") or "."))
    matches = glob_lib.glob(str(root / pattern), recursive=bool(request.arguments.get("recursive", True)))
    return ToolCallResult(
        tool_name=request.tool_name,
        content=matches,
        structured_content={"count": len(matches)},
    )


async def _grep(request: ToolCallRequest) -> ToolCallResult:
    pattern = re.compile(str(request.arguments["pattern"]))
    root = Path(str(request.arguments.get("root") or "."))
    file_pattern = str(request.arguments.get("glob") or "**/*")
    matches: list[dict[str, Any]] = []
    for path in root.glob(file_pattern):
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding=request.arguments.get("encoding") or "utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for index, line in enumerate(lines, start=1):
            if pattern.search(line):
                matches.append({"path": str(path), "line": index, "text": line})
    return ToolCallResult(
        tool_name=request.tool_name,
        content=matches,
        structured_content={"count": len(matches)},
    )


async def _bash(request: ToolCallRequest) -> ToolCallResult:
    command = str(request.arguments["command"])
    timeout = float(request.arguments.get("timeout") or 120)
    completed = await asyncio.to_thread(
        subprocess.run,
        command,
        capture_output=True,
        text=True,
        shell=True,
        timeout=timeout,
    )
    return ToolCallResult(
        tool_name=request.tool_name,
        content=completed.stdout,
        structured_content={
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
        is_error=completed.returncode != 0,
    )


async def _sleep(request: ToolCallRequest) -> ToolCallResult:
    seconds = float(request.arguments.get("seconds") or 1)
    await asyncio.sleep(seconds)
    return ToolCallResult(
        tool_name=request.tool_name,
        content=f"slept {seconds}s",
        structured_content={"seconds": seconds},
    )


async def _todo_write(request: ToolCallRequest) -> ToolCallResult:
    global _todos
    todos = request.arguments.get("todos")
    if todos is None:
        todos = request.arguments.get("items")
    if not isinstance(todos, list):
        raise ToolExecutionError("TodoWrite 需要 todos 列表参数")
    _todos = [dict(item) if isinstance(item, dict) else {"content": str(item)} for item in todos]
    return ToolCallResult(
        tool_name=request.tool_name,
        content=_todos,
        structured_content={"count": len(_todos)},
        raw={"todos": _todos},
    )


async def _list_mcp_resources(request: ToolCallRequest) -> ToolCallResult:
    from src.ai.core.tools.mcp import mcp_manager

    server_key = str(request.arguments["server_key"])
    resources = await mcp_manager.list_resources(server_key)
    return ToolCallResult(
        tool_name=request.tool_name,
        content=resources,
        structured_content={"server_key": server_key, "count": len(resources)},
    )


async def _read_mcp_resource(request: ToolCallRequest) -> ToolCallResult:
    from src.ai.core.tools.mcp import mcp_manager

    server_key = str(request.arguments["server_key"])
    uri = str(request.arguments["uri"])
    result = await mcp_manager.read_resource(server_key=server_key, uri=uri)
    return ToolCallResult(
        tool_name=request.tool_name,
        content=result,
        structured_content={"server_key": server_key, "uri": uri},
        raw=result,
    )


def _file_read_schema() -> dict[str, Any]:
    return _schema({"path": {"type": "string"}, "encoding": {"type": "string"}, "max_bytes": {"type": "integer"}}, ["path"])


def _file_write_schema() -> dict[str, Any]:
    return _schema({"path": {"type": "string"}, "content": {"type": "string"}, "encoding": {"type": "string"}}, ["path", "content"])


def _file_edit_schema() -> dict[str, Any]:
    return _schema({"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}, "count": {"type": "integer"}}, ["path", "old", "new"])


def _glob_schema() -> dict[str, Any]:
    return _schema({"pattern": {"type": "string"}, "root": {"type": "string"}, "recursive": {"type": "boolean"}}, ["pattern"])


def _grep_schema() -> dict[str, Any]:
    return _schema({"pattern": {"type": "string"}, "root": {"type": "string"}, "glob": {"type": "string"}}, ["pattern"])


def _bash_schema() -> dict[str, Any]:
    return _schema({"command": {"type": "string"}, "timeout": {"type": "number"}}, ["command"])


def _sleep_schema() -> dict[str, Any]:
    return _schema({"seconds": {"type": "number"}}, [])


def _todo_schema() -> dict[str, Any]:
    return _schema({"todos": {"type": "array"}}, ["todos"])


def _mcp_resource_list_schema() -> dict[str, Any]:
    return _schema({"server_key": {"type": "string"}}, ["server_key"])


def _mcp_resource_read_schema() -> dict[str, Any]:
    return _schema({"server_key": {"type": "string"}, "uri": {"type": "string"}}, ["server_key", "uri"])


def _schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required}


def tool_result_to_json(result: ToolCallResult) -> str:
    return json.dumps(result.raw or result.structured_content or result.content, ensure_ascii=False)
