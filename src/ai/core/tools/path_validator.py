"""路径验证工具 — 防止路径穿越攻击。"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# 默认允许访问的目录 — 项目根目录和当前工作目录
_PROJECT_ROOT: Path | None = None


def get_project_root() -> Path:
    """获取项目根目录。"""
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        # 从当前文件向上查找到 pyproject.toml 所在目录
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "pyproject.toml").exists():
                _PROJECT_ROOT = parent
                break
        if _PROJECT_ROOT is None:
            # 回退到当前工作目录
            _PROJECT_ROOT = Path.cwd().resolve()
    return _PROJECT_ROOT


def get_allowed_roots() -> list[Path]:
    """获取允许访问的根目录列表。"""
    roots = [get_project_root()]

    # 添加当前工作目录（如果不同于项目根目录）
    cwd = Path.cwd().resolve()
    if cwd != roots[0]:
        roots.append(cwd)

    return roots


def validate_path(path: str | Path, *, must_exist: bool = False) -> Path:
    """验证并规范化路径，防止路径穿越攻击。

    Args:
        path: 待验证的路径。
        must_exist: 是否要求路径必须存在。

    Returns:
        规范化后的绝对路径。

    Raises:
        ValueError: 路径不合法或超出允许范围。
        FileNotFoundError: must_exist=True 且路径不存在。
    """
    # 转换为 Path 对象
    target = Path(path)

    # 解析符号链接，获取真实路径
    try:
        real_path = target.resolve()
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"路径解析失败: {exc}") from exc

    # 检查路径是否在允许的根目录下
    allowed_roots = get_allowed_roots()
    is_allowed = any(
        _is_path_under(real_path, root) for root in allowed_roots
    )

    if not is_allowed:
        raise ValueError(
            f"路径超出允许范围: {target}\n"
            f"允许的根目录: {[str(r) for r in allowed_roots]}"
        )

    # 检查路径是否存在
    if must_exist and not real_path.exists():
        raise FileNotFoundError(f"路径不存在: {target}")

    return real_path


def _is_path_under(path: Path, parent: Path) -> bool:
    """检查路径是否在指定父目录下。

    使用 os.path.commonpath 进行可靠的路径比较。
    """
    try:
        common = Path(os.path.commonpath([str(path), str(parent)]))
        return common == parent
    except ValueError:
        # 不同驱动器（Windows）会抛出 ValueError
        return False


def validate_file_path(path: str | Path) -> Path:
    """验证文件路径（必须存在且是文件）。"""
    real_path = validate_path(path, must_exist=True)
    if not real_path.is_file():
        raise ValueError(f"路径不是文件: {path}")
    return real_path


def validate_dir_path(path: str | Path) -> Path:
    """验证目录路径（必须存在且是目录）。"""
    real_path = validate_path(path, must_exist=True)
    if not real_path.is_dir():
        raise ValueError(f"路径不是目录: {path}")
    return real_path
