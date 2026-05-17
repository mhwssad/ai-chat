"""文件操作工具集 — 供 AI Agent 调用。

提供文件写入（覆盖/追加）、内容替换（精确/正则）、读取（全文/按行/指定编码）三类操作。
所有工具保持纯粹的文件操作，不依赖任何业务类。
"""

import re
from pathlib import Path

from src.ai_chat.tools.registry import ToolType, registered_tool


# ---------------------------------------------------------------------------
# 写入
# ---------------------------------------------------------------------------

@registered_tool(tool_type=ToolType.SYSTEM)
def write_file(file_path: str, content: str, encoding: str = "utf-8") -> str:
    """覆盖写入文件。文件不存在时自动创建（含父目录）。

    Args:
        file_path: 文件路径。
        content: 要写入的完整内容。
        encoding: 字符编码，默认 utf-8。
    """
    path = Path(file_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
        return f"[OK] 覆盖写入成功：{file_path}（{len(content)} 字符）"
    except PermissionError:
        return f"[ERROR] 无写入权限：{file_path}"
    except OSError as e:
        return f"[ERROR] 写入失败：{e}"


@registered_tool(tool_type=ToolType.SYSTEM)
def append_file(file_path: str, content: str, encoding: str = "utf-8") -> str:
    """向文件末尾追加内容。文件不存在时自动创建（含父目录）。

    Args:
        file_path: 文件路径。
        content: 要追加的内容。
        encoding: 字符编码，默认 utf-8。
    """
    path = Path(file_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding=encoding) as f:
            f.write(content)
        return f"[OK] 追加写入成功：{file_path}（追加 {len(content)} 字符）"
    except PermissionError:
        return f"[ERROR] 无写入权限：{file_path}"
    except OSError as e:
        return f"[ERROR] 追加失败：{e}"


# ---------------------------------------------------------------------------
# 替换
# ---------------------------------------------------------------------------

@registered_tool(tool_type=ToolType.SYSTEM)
def replace_exact(file_path: str, old: str, new: str, encoding: str = "utf-8") -> str:
    """按字符串精确匹配，替换文件中的所有匹配项。

    Args:
        file_path: 文件路径。
        old: 要被替换的原始文本（必须与文件中完全一致）。
        new: 替换后的新文本。
        encoding: 字符编码，默认 utf-8。
    """
    path = Path(file_path)
    try:
        original = path.read_text(encoding=encoding)
    except FileNotFoundError:
        return f"[ERROR] 文件不存在：{file_path}"
    except PermissionError:
        return f"[ERROR] 无读取权限：{file_path}"
    except UnicodeDecodeError:
        return f"[ERROR] 编码解码失败，请确认文件编码（当前：{encoding}）"
    except OSError as e:
        return f"[ERROR] 读取失败：{e}"

    count = original.count(old)
    if count == 0:
        return f"[INFO] 未找到匹配文本，未做修改：{file_path}"

    new_content = original.replace(old, new)
    try:
        path.write_text(new_content, encoding=encoding)
        return f"[OK] 精确替换成功：{file_path}（{count} 处替换）"
    except PermissionError:
        return f"[ERROR] 无写入权限：{file_path}"
    except OSError as e:
        return f"[ERROR] 写入失败：{e}"


@registered_tool(tool_type=ToolType.SYSTEM)
def replace_regex(file_path: str, pattern: str, replacement: str, encoding: str = "utf-8") -> str:
    """按正则表达式匹配，替换文件中的所有匹配项。

    Args:
        file_path: 文件路径。
        pattern: 正则表达式。
        replacement: 替换文本（支持 \\1 等分组引用）。
        encoding: 字符编码，默认 utf-8。
    """
    path = Path(file_path)
    try:
        original = path.read_text(encoding=encoding)
    except FileNotFoundError:
        return f"[ERROR] 文件不存在：{file_path}"
    except PermissionError:
        return f"[ERROR] 无读取权限：{file_path}"
    except UnicodeDecodeError:
        return f"[ERROR] 编码解码失败，请确认文件编码（当前：{encoding}）"
    except OSError as e:
        return f"[ERROR] 读取失败：{e}"

    try:
        compiled = re.compile(pattern)
    except re.error as e:
        return f"[ERROR] 正则表达式无效：{e}"

    new_content, count = compiled.subn(replacement, original)
    if count == 0:
        return f"[INFO] 未找到正则匹配，未做修改：{file_path}"

    try:
        path.write_text(new_content, encoding=encoding)
        return f"[OK] 正则替换成功：{file_path}（{count} 处替换）"
    except PermissionError:
        return f"[ERROR] 无写入权限：{file_path}"
    except OSError as e:
        return f"[ERROR] 写入失败：{e}"


# ---------------------------------------------------------------------------
# 读取
# ---------------------------------------------------------------------------

@registered_tool(tool_type=ToolType.SYSTEM)
def read_file(file_path: str, encoding: str = "utf-8") -> str:
    """读取文件的全部内容。

    Args:
        file_path: 文件路径。
        encoding: 字符编码，默认 utf-8。
    """
    path = Path(file_path)
    if not path.exists():
        return f"[ERROR] 文件不存在：{file_path}"
    if not path.is_file():
        return f"[ERROR] 路径不是文件：{file_path}"
    try:
        return path.read_text(encoding=encoding)
    except PermissionError:
        return f"[ERROR] 无读取权限：{file_path}"
    except UnicodeDecodeError:
        return f"[ERROR] 编码解码失败，请确认文件编码（当前：{encoding}）"
    except OSError as e:
        return f"[ERROR] 读取失败：{e}"


@registered_tool(tool_type=ToolType.SYSTEM)
def read_lines(file_path: str, start: int = 1, end: int = 0, encoding: str = "utf-8") -> str:
    """按行读取文件内容，支持指定行号范围（从 1 开始）。

    Args:
        file_path: 文件路径。
        start: 起始行号（从 1 开始），默认 1。
        end: 结束行号（包含），0 表示读到末尾，默认 0。
        encoding: 字符编码，默认 utf-8。
    """
    path = Path(file_path)
    if not path.exists():
        return f"[ERROR] 文件不存在：{file_path}"
    if not path.is_file():
        return f"[ERROR] 路径不是文件：{file_path}"

    try:
        with path.open("r", encoding=encoding) as f:
            lines = f.readlines()
    except PermissionError:
        return f"[ERROR] 无读取权限：{file_path}"
    except UnicodeDecodeError:
        return f"[ERROR] 编码解码失败，请确认文件编码（当前：{encoding}）"
    except OSError as e:
        return f"[ERROR] 读取失败：{e}"

    total = len(lines)
    actual_end = total if end <= 0 else min(end, total)
    actual_start = max(1, start)

    if actual_start > total:
        return f"[INFO] 起始行 {actual_start} 超出文件总行数（{total} 行）"

    selected = lines[actual_start - 1 : actual_end]
    numbered = [f"{i + actual_start:>4} | {line}" for i, line in enumerate(selected)]
    return "".join(numbered)
