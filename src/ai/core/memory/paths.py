"""记忆路径解析与安全校验。"""

from __future__ import annotations

import re
from pathlib import Path

from src.ai.config.base_config import project_root

from .errors import MemoryPathError


class MemoryPathResolver:
    """解析自动记忆和团队记忆路径。"""

    def __init__(self, *, memory_base: str | Path | None = None) -> None:
        self._memory_base = Path(memory_base) if memory_base else project_root / "data" / "memory"

    def auto_memory_dir(self, *, git_root: str | Path | None = None, override: str | Path | None = None) -> Path:
        if override:
            return validate_memory_path(override)
        root = Path(git_root) if git_root else project_root
        name = sanitize_path_name(str(root.resolve()))
        return validate_memory_path(self._memory_base / "projects" / name / "memory")

    def team_memory_dir(self, team_name: str) -> Path:
        if not team_name.strip():
            raise MemoryPathError("团队名称不能为空")
        return validate_memory_path(self._memory_base / "teams" / sanitize_path_name(team_name) / "memory")


def validate_memory_path(raw: str | Path) -> Path:
    """校验记忆路径，拒绝危险路径。"""
    text = str(raw)
    if "\x00" in text:
        raise MemoryPathError("记忆路径包含 null 字节")
    if text.startswith("\\\\"):
        raise MemoryPathError("记忆路径不允许使用 UNC 路径", context={"path": text})
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = project_root / path
    resolved = path.resolve()
    anchor = Path(resolved.anchor)
    if resolved == anchor:
        raise MemoryPathError("记忆路径不能是磁盘根目录", context={"path": str(resolved)})
    return resolved


def sanitize_path_name(value: str) -> str:
    """将路径或团队名称转换为稳定目录名。"""
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-") or "default"

