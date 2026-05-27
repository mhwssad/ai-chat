"""搜索工具。"""

import glob as glob_lib
import json
import re
from pathlib import Path

from langchain_core.tools import tool

from src.ai.core.tools.registry import register_tool


@tool
async def glob_files(pattern: str, root: str = ".") -> str:
    """按 glob 模式搜索文件。

    Args:
        pattern: glob 模式（如 "**/*.py"）。
        root: 搜索根目录。
    """
    root_path = Path(root)
    matches = glob_lib.glob(str(root_path / pattern), recursive=True)
    if not matches:
        return "未找到匹配文件"
    return "\n".join(sorted(matches))


@tool
async def grep(pattern: str, root: str = ".", glob: str = "**/*") -> str:
    """使用正则表达式搜索文件内容。

    Args:
        pattern: 正则表达式。
        root: 搜索根目录。
        glob: 文件过滤模式。
    """
    regex = re.compile(pattern)
    root_path = Path(root)
    matches: list[dict[str, str | int]] = []
    for path in root_path.glob(glob):
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for index, line in enumerate(lines, start=1):
            if regex.search(line):
                matches.append({"path": str(path), "line": index, "text": line})
    if not matches:
        return "未找到匹配内容"
    return json.dumps(matches[:200], ensure_ascii=False, indent=2)


@tool
async def tool_search(query: str = "", source_type: str | None = None) -> str:
    """搜索可用工具。

    Args:
        query: 搜索关键词。
        source_type: 按来源类型过滤（builtin / mcp）。
    """
    from src.ai.core.tools.registry import tool_registry

    all_tools = tool_registry.list(enabled_only=True)
    if source_type:
        all_tools = [t for t in all_tools if getattr(t, "source_type", "builtin") == source_type]

    if query:
        q = query.lower()
        matched = [
            t for t in all_tools
            if q in t.name.lower() or q in (t.description or "").lower()
        ]
    else:
        matched = all_tools

    if not matched:
        return "未找到匹配的工具"

    lines = [
        f"- {t.name} ({getattr(t, 'source_type', 'builtin')}): {t.description or ''}"
        for t in matched
    ]
    return f"找到 {len(matched)} 个工具:\n" + "\n".join(lines)


# ── 自注册 ──────────────────────────────────────────────────────────────────

register_tool(glob_files, source_type="builtin", permissions=["file_read"], essential=True)
register_tool(grep, source_type="builtin", permissions=["file_read"], essential=True)
register_tool(tool_search, source_type="builtin", essential=True)
