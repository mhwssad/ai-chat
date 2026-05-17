"""工具模块内部共享辅助函数。"""

from pathlib import Path

from src.ai_chat.config.base_config import project_root


def resolve_project_path(raw_path: str) -> Path:
    """将原始路径解析为项目内的绝对路径。

    相对路径会基于 project_root 解析。
    """
    path = Path(raw_path)
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def is_within_project(path: Path) -> bool:
    """判断路径是否在项目根目录内。"""
    try:
        path.relative_to(project_root)
        return True
    except ValueError:
        return False


def ensure_project_path(raw_path: str) -> Path:
    """解析路径并确保其在项目根目录内，否则抛出 ValueError。"""
    path = resolve_project_path(raw_path)
    if not is_within_project(path):
        raise ValueError(f"路径超出项目根目录：{raw_path}")
    return path


def to_project_relative(path: Path) -> str:
    """将绝对路径转换为相对于项目根目录的路径字符串。"""
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)
