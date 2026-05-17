"""文本搜索工具 — 按文件内容检索匹配行。"""

from src.ai_chat.tools._helpers import resolve_project_path, is_within_project, project_root
from src.ai_chat.tools.registry import ToolType, registered_tool

# 单个搜索文件的最大大小（1MB），超过则跳过
_MAX_SEARCH_FILE_SIZE = 1_048_576


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
    root = resolve_project_path(root_dir)
    if not is_within_project(root):
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
            if path.stat().st_size > _MAX_SEARCH_FILE_SIZE:
                continue
            content = path.read_text(encoding=encoding)
        except (UnicodeDecodeError, OSError):
            continue

        rel_path_str = str(path.relative_to(project_root))
        for lineno, line in enumerate(content.splitlines(), start=1):
            if pattern in line:
                matches.append(f"{rel_path_str}:{lineno}: {line.rstrip()}")
                if len(matches) >= max_matches:
                    return "\n".join(matches)

    if not matches:
        return f"[INFO] 未找到匹配内容：{pattern}"
    return "\n".join(matches)
