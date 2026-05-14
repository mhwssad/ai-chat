"""文本搜索工具 — 按文件内容检索匹配行。"""

from pathlib import Path

from src.ai_chat.tools.registry import ToolType, registered_tool

project_root = Path(__file__).resolve().parents[3]


def _resolve_root(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


@registered_tool(tool_type=ToolType.SYSTEM)
def search_text(
    pattern: str,
    root_dir: str = ".",
    file_glob: str = "*",
    max_matches: int = 50,
    encoding: str = "utf-8",
) -> str:
    """在目录下递归搜索文本，返回匹配的文件和行号。

    Args:
        pattern: 要搜索的文本片段。
        root_dir: 搜索根目录，默认当前目录。
        file_glob: 文件匹配模式，如 ``*.py``。
        max_matches: 最多返回的匹配条数。
        encoding: 文本读取编码，默认 utf-8。
    """
    root = _resolve_root(root_dir)
    try:
        root.relative_to(project_root)
    except ValueError:
        return f"[ERROR] 路径超出项目根目录：{root_dir}"

    if not root.exists():
        return f"[ERROR] 路径不存在：{root_dir}"
    if not root.is_dir():
        return f"[ERROR] 路径不是目录：{root_dir}"
    if max_matches <= 0:
        return "[ERROR] max_matches 必须大于 0"
    if not pattern:
        return "[ERROR] pattern 不能为空"

    matches: list[str] = []
    for path in sorted(root.rglob(file_glob)):
        if not path.is_file():
            continue
        try:
            with path.open("r", encoding=encoding) as file:
                for lineno, line in enumerate(file, start=1):
                    if pattern in line:
                        rel_path = path.relative_to(project_root)
                        matches.append(f"{rel_path}:{lineno}: {line.rstrip()}")
                        if len(matches) >= max_matches:
                            return "\n".join(matches)
        except (UnicodeDecodeError, OSError):
            continue

    if not matches:
        return f"[INFO] 未找到匹配内容：{pattern}"
    return "\n".join(matches)
