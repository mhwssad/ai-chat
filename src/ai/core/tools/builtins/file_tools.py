"""文件操作工具。"""

import json

from langchain_core.tools import tool

from src.ai.core.tools.path_validator import validate_file_path, validate_path
from src.ai.core.tools.register import register_tool
from src.ai.utils.thread_pool import get_thread_pool


@tool
async def file_read(
    path: str, encoding: str = "utf-8", max_bytes: int = 1048576
) -> str:
    """读取本地文件内容。

    Args:
        path: 文件路径。
        encoding: 文件编码。
        max_bytes: 最大读取字节数。
    """
    file_path = validate_file_path(path)
    pool = get_thread_pool()
    data = await pool.run_io(file_path.read_bytes)
    truncated = len(data) > max_bytes
    data = data[:max_bytes]
    try:
        content = data.decode(encoding)
    except UnicodeDecodeError:
        content = data.hex()
    if truncated:
        content += "\n... [已截断]"
    return content


@tool
async def file_write(path: str, content: str, encoding: str = "utf-8") -> str:
    """创建或覆盖文件。

    Args:
        path: 文件路径。
        content: 文件内容。
        encoding: 文件编码。
    """
    file_path = validate_path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    pool = get_thread_pool()
    await pool.run_io(file_path.write_text, content, encoding)
    return f"已写入: {file_path} ({len(content.encode('utf-8'))} bytes)"


@tool
async def edit_file(path: str, old: str, new: str, count: int = 1) -> str:
    """对文件进行字符串替换。

    Args:
        path: 文件路径。
        old: 待替换文本。
        new: 替换为。
        count: 替换次数，-1 表示全部。
    """
    file_path = validate_file_path(path)
    pool = get_thread_pool()
    text = await pool.run_io(file_path.read_text, "utf-8")
    if old not in text:
        return f"错误: 待替换内容不存在于 {file_path}"
    actual_count = text.count(old) if count < 0 else min(text.count(old), count)
    updated = text.replace(old, new, count)
    await pool.run_io(file_path.write_text, updated, "utf-8")
    return f"已编辑: {file_path} ({actual_count} 处替换)"


@tool
async def file_json_read(path: str) -> str:
    """读取 JSON 文件并返回格式化内容。

    Args:
        path: JSON 文件路径。
    """
    file_path = validate_file_path(path)
    pool = get_thread_pool()
    data = await pool.run_io(file_path.read_text, "utf-8")
    parsed = json.loads(data)
    return json.dumps(parsed, ensure_ascii=False, indent=2)


# ── 自注册 ──────────────────────────────────────────────────────────────────

register_tool(
    file_read, source_type="builtin", permissions=["file_read"], essential=True
)
register_tool(
    file_write, source_type="builtin", permissions=["file_write"], essential=True
)
register_tool(
    edit_file,
    source_type="builtin",
    permissions=["file_read", "file_write"],
    essential=True,
)
register_tool(file_json_read, source_type="builtin", permissions=["file_read"])
