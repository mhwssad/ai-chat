"""项目内路径与目录工具。"""

import json
from pathlib import Path

from src.ai_chat.tools._helpers import ensure_project_path, to_project_relative
from src.ai_chat.tools.registry import ToolType, registered_tool


def _walk_with_depth(directory: Path, max_depth: int):
    """递归遍历目录，限制最大深度。"""

    def _walk(current: Path, depth: int):
        if depth > max_depth:
            return
        try:
            for item in sorted(current.iterdir()):
                yield item
                if item.is_dir():
                    yield from _walk(item, depth + 1)
        except PermissionError:
            pass

    yield from _walk(directory, 0)


@registered_tool(tool_type=ToolType.SYSTEM)
def list_dir(
    path: str = ".",
    recursive: bool = False,
    include_hidden: bool = False,
    max_depth: int = 5,
) -> str:
    """列出项目内目录内容。"""
    try:
        target = ensure_project_path(path)
    except ValueError as e:
        return f"[ERROR] {e}"

    if not target.exists():
        return f"[ERROR] 路径不存在：{path}"
    if not target.is_dir():
        return f"[ERROR] 路径不是目录：{path}"

    if recursive:
        iterator = _walk_with_depth(target, max_depth)
    else:
        iterator = target.iterdir()

    entries = []
    for item in sorted(iterator) if not recursive else iterator:
        if not include_hidden and item.name.startswith("."):
            continue
        entries.append({
            "name": item.name,
            "type": "dir" if item.is_dir() else "file",
            "path": to_project_relative(item),
        })

    return json.dumps({
        "ok": True,
        "path": to_project_relative(target),
        "entries": entries,
    }, ensure_ascii=False, indent=2)


@registered_tool(tool_type=ToolType.SYSTEM)
def path_info(path: str) -> str:
    """查看项目内路径信息。"""
    try:
        target = ensure_project_path(path)
    except ValueError as e:
        return f"[ERROR] {e}"

    exists = target.exists()
    info = {
        "ok": True,
        "input": path,
        "exists": exists,
        "absolute_path": str(target),
        "relative_path": to_project_relative(target),
        "type": (
            "dir" if target.is_dir() else
            "file" if target.is_file() else
            "missing"
        ),
        "size": target.stat().st_size if exists and target.is_file() else None,
    }
    return json.dumps(info, ensure_ascii=False, indent=2)


@registered_tool(tool_type=ToolType.SYSTEM)
def make_dir(path: str, parents: bool = True) -> str:
    """在项目根目录内创建目录。"""
    try:
        target = ensure_project_path(path)
    except ValueError as e:
        return f"[ERROR] {e}"

    try:
        target.mkdir(parents=parents, exist_ok=True)
    except OSError as e:
        return f"[ERROR] 创建目录失败：{e}"

    return json.dumps({
        "ok": True,
        "created": True,
        "path": to_project_relative(target),
    }, ensure_ascii=False, indent=2)


@registered_tool(tool_type=ToolType.SYSTEM)
def glob_files(pattern: str, root_dir: str = ".") -> str:
    """按 glob 模式在项目内查找文件。"""
    try:
        root = ensure_project_path(root_dir)
    except ValueError as e:
        return f"[ERROR] {e}"

    if not root.exists():
        return f"[ERROR] 路径不存在：{root_dir}"
    if not root.is_dir():
        return f"[ERROR] 路径不是目录：{root_dir}"
    if not pattern:
        return "[ERROR] pattern 不能为空"

    matches = [
        to_project_relative(path)
        for path in sorted(root.rglob(pattern))
        if path.is_file()
    ]
    return json.dumps({
        "ok": True,
        "root_dir": to_project_relative(root),
        "pattern": pattern,
        "matches": matches,
    }, ensure_ascii=False, indent=2)
