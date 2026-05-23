"""记忆文件扫描。"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .errors import MemoryScanError
from .types import MEMORY_TYPES, MemoryHeader, MemoryType

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


class MemoryScanner:
    """扫描记忆目录中的 Markdown 文件。"""

    def scan(self, memory_dir: str | Path, *, limit: int = 200) -> list[MemoryHeader]:
        root = Path(memory_dir)
        if not root.exists():
            return []
        if not root.is_dir():
            raise MemoryScanError("记忆路径不是目录", context={"path": str(root)})
        headers: list[MemoryHeader] = []
        for path in root.rglob("*.md"):
            if path.name == "MEMORY.md":
                continue
            header = self._read_header(path)
            if header is not None:
                headers.append(header)
        return sorted(headers, key=lambda item: item.modified_at, reverse=True)[:limit]

    def read_memory_file(self, path: str | Path) -> str:
        return Path(path).read_text(encoding="utf-8")

    def read_entrypoint(self, memory_dir: str | Path) -> str:
        entrypoint = Path(memory_dir) / "MEMORY.md"
        if not entrypoint.exists():
            return ""
        return entrypoint.read_text(encoding="utf-8")

    def _read_header(self, path: Path) -> MemoryHeader | None:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")
        match = FRONTMATTER_RE.match(text)
        if match is None:
            return None
        data = parse_frontmatter(match.group(1))
        memory_type = data.get("type", "project")
        if memory_type not in MEMORY_TYPES:
            memory_type = "project"
        return MemoryHeader(
            path=str(path.resolve()),
            memory_type=memory_type,  # type: ignore[arg-type]
            description=str(data.get("description") or path.stem),
            modified_at=datetime.fromtimestamp(path.stat().st_mtime),
            metadata=data,
        )


def parse_frontmatter(text: str) -> dict[str, Any]:
    """解析简单 YAML frontmatter。"""
    data: dict[str, Any] = {}
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("\"'")
    return data

