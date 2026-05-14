"""项目内路径与目录工具。"""

import json
from pathlib import Path

from src.ai_chat.tools.registry import ToolType, registered_tool

project_root = Path(__file__).resolve().parents[3]


def _resolve_project_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def _is_within_project(path: Path) -> bool:
    try:
        path.relative_to(project_root)
        return True
    except ValueError:
        return False


def _ensure_project_path(raw_path: str) -> Path:
    path = _resolve_project_path(raw_path)
    if not _is_within_project(path):
        raise ValueError(f"路径超出项目根目录：{raw_path}")
    return path


def _to_project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


@registered_tool(tool_type=ToolType.SYSTEM)
def list_dir(path: str = ".", recursive: bool = False, include_hidden: bool = False) -> str:
    """列出项目内目录内容。"""
    try:
        target = _ensure_project_path(path)
    except ValueError as e:
        return f"[ERROR] {e}"

    if not target.exists():
        return f"[ERROR] 路径不存在：{path}"
    if not target.is_dir():
        return f"[ERROR] 路径不是目录：{path}"

    entries = []
    iterator = target.rglob("*") if recursive else target.iterdir()
    for item in sorted(iterator):
        if not include_hidden and item.name.startswith("."):
            continue
        entries.append({
            "name": item.name,
            "type": "dir" if item.is_dir() else "file",
            "path": _to_project_relative(item),
        })

    return json.dumps({
        "ok": True,
        "path": _to_project_relative(target),
        "entries": entries,
    }, ensure_ascii=False, indent=2)


@registered_tool(tool_type=ToolType.SYSTEM)
def path_info(path: str) -> str:
    """查看项目内路径信息。"""
    try:
        target = _ensure_project_path(path)
    except ValueError as e:
        return f"[ERROR] {e}"

    exists = target.exists()
    info = {
        "ok": True,
        "input": path,
        "exists": exists,
        "absolute_path": str(target),
        "relative_path": _to_project_relative(target),
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
        target = _ensure_project_path(path)
    except ValueError as e:
        return f"[ERROR] {e}"

    try:
        target.mkdir(parents=parents, exist_ok=True)
    except OSError as e:
        return f"[ERROR] 创建目录失败：{e}"

    return json.dumps({
        "ok": True,
        "created": True,
        "path": _to_project_relative(target),
    }, ensure_ascii=False, indent=2)


@registered_tool(tool_type=ToolType.SYSTEM)
def glob_files(pattern: str, root_dir: str = ".") -> str:
    """按 glob 模式在项目内查找文件。"""
    try:
        root = _ensure_project_path(root_dir)
    except ValueError as e:
        return f"[ERROR] {e}"

    if not root.exists():
        return f"[ERROR] 路径不存在：{root_dir}"
    if not root.is_dir():
        return f"[ERROR] 路径不是目录：{root_dir}"
    if not pattern:
        return "[ERROR] pattern 不能为空"

    matches = [
        _to_project_relative(path)
        for path in sorted(root.rglob(pattern))
        if path.is_file()
    ]
    return json.dumps({
        "ok": True,
        "root_dir": _to_project_relative(root),
        "pattern": pattern,
        "matches": matches,
    }, ensure_ascii=False, indent=2)
