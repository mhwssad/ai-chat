"""搜索工具。"""

import glob as glob_lib
import json
import re

from langchain_core.tools import tool

from src.ai.core.tools.path_validator import validate_dir_path
from src.ai.core.tools.register import register_tool


@tool
async def glob_files(pattern: str, root: str = ".") -> str:
    """按 glob 模式搜索文件。

    Args:
        pattern: glob 模式（如 "**/*.py"）。
        root: 搜索根目录。
    """
    root_path = validate_dir_path(root)
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
    root_path = validate_dir_path(root)
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


def create_tool_search_tool(registry):
    """工厂函数：创建绑定了 registry 的 tool_search 工具。"""

    @tool
    async def tool_search(query: str = "", source_type: str | None = None) -> str:
        """搜索可用工具。

        Args:
            query: 搜索关键词。
            source_type: 按来源类型过滤（builtin / mcp / skill）。
        """
        all_tools = registry.list(enabled_only=True)
        if source_type:
            all_tools = [
                t
                for t in all_tools
                if registry.get_meta(t.name).source_type == source_type
            ]

        if query:
            q = query.lower()
            matched = [
                t
                for t in all_tools
                if q in t.name.lower() or q in (t.description or "").lower()
            ]
        else:
            matched = all_tools

        if not matched:
            return "未找到匹配的工具"

        lines = [
            f"- {t.name} ({registry.get_meta(t.name).source_type}): {t.description or ''}"
            for t in matched
        ]
        return f"找到 {len(matched)} 个工具:\n" + "\n".join(lines)

    return tool_search


def create_tool_search_schema_tool(registry):
    """工厂函数：创建绑定了 registry 的 tool_search_schema 工具。"""

    @tool
    async def tool_search_schema(query: str = "") -> str:
        """搜索工具并返回完整 JSON schema（含参数定义）。

        Args:
            query: 搜索关键词，空字符串返回所有已启用工具的 schema。
        """
        matched = registry.search(query) if query else registry.list(enabled_only=True)
        if not matched:
            return "未找到匹配的工具"

        schemas = []
        for t in matched:
            params = (
                t.args_schema.model_json_schema()
                if t.args_schema
                else {"type": "object", "properties": {}}
            )
            schemas.append(
                {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": params,
                }
            )
        return json.dumps(schemas, ensure_ascii=False, indent=2)

    return tool_search_schema


def register(registry):
    """注册搜索工具。"""
    tool_search_fn = create_tool_search_tool(registry)
    tool_search_schema_fn = create_tool_search_schema_tool(registry)
    register_tool(
        glob_files, source_type="builtin", permissions=["file_read"], essential=True
    )
    register_tool(
        grep, source_type="builtin", permissions=["file_read"], essential=True
    )
    register_tool(tool_search_fn, source_type="builtin", essential=True)
    register_tool(tool_search_schema_fn, source_type="builtin", essential=True)
