"""基于文件系统的记忆存储和索引管理。

存储结构：
{memory_dir}/
  sessions/
    default.md              ← 无 session_id 的记忆
    {session_id}.md         ← 会话记忆（多条目）
  MEMORY.md                 ← 索引

职责分离：
- MemoryStore: 会话文件的 CRUD 操作
- MemoryIndex: MEMORY.md 索引的读写和统计
"""

from datetime import datetime
from pathlib import Path

from .frontmatter import (
    format_entry_append,
    format_session_file,
    parse_session_file,
)
from .types import MemoryEntry, MemoryType


def _slug(value: str) -> str:
    """将文本转为文件名安全的 slug。"""
    cleaned = "".join(
        ch if ch.isalnum() or ch in "._-" else "-" for ch in value.lower()
    ).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned[:48] or "memory"


class MemoryIndex:
    """MEMORY.md 索引管理。

    负责索引文件的读取、重建和增量更新，不涉及会话文件的 CRUD。
    """

    def __init__(self, memory_dir: Path) -> None:
        self._dir = memory_dir
        self._index_path = memory_dir / "MEMORY.md"

    def read(self) -> str:
        """读取 MEMORY.md 索引原始内容。"""
        if not self._index_path.exists():
            return ""
        return self._index_path.read_text(encoding="utf-8")

    def rebuild(self, entries: list[MemoryEntry]) -> None:
        """根据记忆条目列表重建 MEMORY.md 索引。"""
        self._dir.mkdir(parents=True, exist_ok=True)
        lines = ["# Memory Index", ""]
        for entry in entries:
            rel_path = (
                entry.file_path.relative_to(self._dir) if entry.file_path else Path("")
            )
            lines.append(f"- [{entry.name}]({rel_path}) — {entry.description}")
        self._index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def append_entry(self, entry: MemoryEntry, file_path: Path) -> None:
        """增量追加单条记忆到索引。"""
        self._dir.mkdir(parents=True, exist_ok=True)
        rel_path = file_path.relative_to(self._dir)
        line = f"- [{entry.name}]({rel_path}) — {entry.description}\n"

        if self._index_path.exists():
            content = self._index_path.read_text(encoding="utf-8")
            if entry.name not in content:
                content = content.rstrip("\n") + "\n" + line
                self._index_path.write_text(content, encoding="utf-8")
        else:
            self._index_path.write_text("# Memory Index\n\n" + line, encoding="utf-8")

    @staticmethod
    def compute_stats(entries: list[MemoryEntry]) -> dict[str, int]:
        """根据条目列表计算各类记忆的数量统计。"""
        stats: dict[str, int] = {"total": len(entries)}
        for entry in entries:
            stats[entry.memory_type] = stats.get(entry.memory_type, 0) + 1
        return stats


class MemoryStore:
    """基于文件系统的记忆存储。

    每个会话对应一个文件：{memory_dir}/sessions/{session_id}.md
    文件内包含多条记忆条目，每个条目有自己的 frontmatter。
    索引管理委托给 MemoryIndex。

    缓存策略：
    - 使用文件修改时间检测缓存失效
    - list_all() 结果被缓存，文件变更时自动刷新
    """

    def __init__(self, memory_dir: Path, *, index: MemoryIndex | None = None) -> None:
        self._dir = memory_dir
        self._sessions_dir = memory_dir / "sessions"
        self._index = index or MemoryIndex(memory_dir)
        # 缓存：(entries, file_mtimes)
        self._cache: list[MemoryEntry] | None = None
        self._cache_mtimes: dict[Path, float] = {}

    @property
    def memory_dir(self) -> Path:
        return self._dir

    @property
    def index(self) -> MemoryIndex:
        """获取索引管理器。"""
        return self._index

    def write(self, entry: MemoryEntry) -> Path:
        """写入记忆到会话文件。

        如果会话文件已存在，追加条目；否则创建新文件。
        """
        self._ensure_dirs()
        session_id = entry.session_id or "default"
        file_path = self._sessions_dir / f"{_slug(session_id)}.md"

        if file_path.exists():
            existing_text = file_path.read_text(encoding="utf-8")
            append_text = format_entry_append(entry)
            file_path.write_text(existing_text + "\n" + append_text, encoding="utf-8")
        else:
            file_path.write_text(
                format_session_file(session_id, [entry]),
                encoding="utf-8",
            )

        self._index.append_entry(entry, file_path)
        self._invalidate_cache()
        return file_path

    def read(self, file_path: Path) -> MemoryEntry | None:
        """读取指定路径的记忆文件（返回第一个条目）。"""
        entries = parse_session_file(file_path)
        return entries[0] if entries else None

    def delete(self, name: str) -> bool:
        """按 name 删除记忆条目。"""
        for file_path in self._session_files():
            entries = parse_session_file(file_path)
            new_entries = [e for e in entries if e.name != name]
            if len(new_entries) < len(entries):
                if new_entries:
                    session_id = new_entries[0].session_id or "default"
                    file_path.write_text(
                        format_session_file(session_id, new_entries),
                        encoding="utf-8",
                    )
                else:
                    file_path.unlink(missing_ok=True)
                self._invalidate_cache()
                self._index.rebuild(self.list_all())
                return True
        return False

    def list_all(self) -> list[MemoryEntry]:
        """列出所有记忆条目（带缓存）。"""
        if self._is_cache_valid():
            return self._cache  # type: ignore[return-value]

        entries: list[MemoryEntry] = []
        new_mtimes: dict[Path, float] = {}
        for file_path in self._session_files():
            entries.extend(parse_session_file(file_path))
            new_mtimes[file_path] = file_path.stat().st_mtime

        entries.sort(key=lambda e: e.created_at or datetime.min, reverse=True)
        self._cache = entries
        self._cache_mtimes = new_mtimes
        return entries

    def list_by_type(self, memory_type: MemoryType) -> list[MemoryEntry]:
        """按类型列出记忆条目。"""
        return [e for e in self.list_all() if e.memory_type == memory_type]

    def get_by_name(self, name: str) -> MemoryEntry | None:
        """按 name 获取单个记忆。"""
        for entry in self.list_all():
            if entry.name == name:
                return entry
        return None

    def _invalidate_cache(self) -> None:
        """使缓存失效。"""
        self._cache = None
        self._cache_mtimes.clear()

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效（基于文件修改时间）。"""
        if self._cache is None:
            return False

        current_files = set(self._session_files())
        cached_files = set(self._cache_mtimes.keys())

        # 文件集合变化
        if current_files != cached_files:
            return False

        # 检查文件修改时间
        for file_path in current_files:
            try:
                current_mtime = file_path.stat().st_mtime
                if current_mtime != self._cache_mtimes.get(file_path):
                    return False
            except OSError:
                return False

        return True

    def _ensure_dirs(self) -> None:
        """确保记忆目录存在。"""
        self._dir.mkdir(parents=True, exist_ok=True)
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_files(self) -> list[Path]:
        """列出所有会话文件。"""
        if not self._sessions_dir.exists():
            return []
        return sorted(self._sessions_dir.glob("*.md"))
