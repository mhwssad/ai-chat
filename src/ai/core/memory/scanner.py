"""记忆文件扫描。"""

from datetime import datetime
from pathlib import Path

from src.ai.exception.memory_exception import MemoryScanError
from .frontmatter import parse_session_file
from .types import MemoryEntry


class MemoryScanner:
    """扫描记忆目录中的会话文件。"""

    def scan(self, memory_dir: str | Path, *, limit: int = 200) -> list[MemoryEntry]:
        root = Path(memory_dir)
        if not root.exists():
            return []
        if not root.is_dir():
            raise MemoryScanError("记忆路径不是目录", context={"path": str(root)})

        sessions_dir = root / "sessions"
        if not sessions_dir.exists():
            return []

        entries: list[MemoryEntry] = []
        for path in sessions_dir.glob("*.md"):
            entries.extend(parse_session_file(path))
        return sorted(entries, key=lambda item: item.created_at or datetime.min, reverse=True)[:limit]

    def read_memory_file(self, path: str | Path) -> str:
        return Path(path).read_text(encoding="utf-8")

    def read_entrypoint(self, memory_dir: str | Path) -> str:
        entrypoint = Path(memory_dir) / "MEMORY.md"
        if not entrypoint.exists():
            return ""
        return entrypoint.read_text(encoding="utf-8")

