"""基于文件系统的记忆存储，管理 MEMORY.md 索引和会话记忆文件。

存储结构：
{memory_dir}/
  sessions/
    default.md              ← 无 session_id 的记忆
    {session_id}.md         ← 会话记忆（多条目）
  MEMORY.md                 ← 索引
"""

import re
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
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in value.lower()).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned[:48] or "memory"


class MemoryStore:
    """基于文件系统的记忆存储，管理 MEMORY.md 索引和会话记忆文件。

    每个会话对应一个文件：{memory_dir}/sessions/{session_id}.md
    文件内包含多条记忆条目，每个条目有自己的 frontmatter。
    """

    def __init__(self, memory_dir: Path) -> None:
        self._dir = memory_dir
        self._sessions_dir = memory_dir / "sessions"
        self._index_path = memory_dir / "MEMORY.md"

    @property
    def memory_dir(self) -> Path:
        return self._dir

    def write(self, entry: MemoryEntry) -> Path:
        """写入记忆到会话文件。

        如果会话文件已存在，追加条目；否则创建新文件。
        """
        self._ensure_dirs()
        session_id = entry.session_id or "default"
        file_path = self._sessions_dir / f"{_slug(session_id)}.md"

        if file_path.exists():
            # 追加到已有文件
            existing_text = file_path.read_text(encoding="utf-8")
            append_text = format_entry_append(entry)
            file_path.write_text(existing_text + "\n" + append_text, encoding="utf-8")
        else:
            # 创建新文件
            file_path.write_text(
                format_session_file(session_id, [entry]),
                encoding="utf-8",
            )

        self._update_index(entry, file_path)
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
                    # 重写文件（保留其他条目）
                    session_id = new_entries[0].session_id or "default"
                    file_path.write_text(
                        format_session_file(session_id, new_entries),
                        encoding="utf-8",
                    )
                else:
                    # 文件为空，删除
                    file_path.unlink(missing_ok=True)
                self.rebuild_index()
                return True
        return False

    def list_all(self) -> list[MemoryEntry]:
        """列出所有记忆条目。"""
        entries: list[MemoryEntry] = []
        for file_path in self._session_files():
            entries.extend(parse_session_file(file_path))
        entries.sort(key=lambda e: e.created_at or datetime.min, reverse=True)
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

    def read_index(self) -> str:
        """读取 MEMORY.md 索引内容。"""
        if not self._index_path.exists():
            return ""
        return self._index_path.read_text(encoding="utf-8")

    def rebuild_index(self) -> None:
        """扫描所有记忆文件，重建 MEMORY.md 索引。"""
        self._ensure_dirs()
        entries = self.list_all()
        lines = ["# Memory Index", ""]
        for entry in entries:
            rel_path = entry.file_path.relative_to(self._dir) if entry.file_path else Path("")
            lines.append(f"- [{entry.name}]({rel_path}) — {entry.description}")
        self._index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def search_files(self, query: str, *, limit: int = 10) -> list[tuple[MemoryEntry, float]]:
        """搜索记忆文件内容，返回匹配结果和分数。"""
        query_lower = query.lower()
        results: list[tuple[MemoryEntry, float]] = []
        for entry in self.list_all():
            score = 0.0
            content_lower = entry.content.lower()
            desc_lower = entry.description.lower()
            if query_lower in content_lower:
                score = 1.0
            elif query_lower in desc_lower:
                score = 0.8
            else:
                query_terms = set(re.split(r"\W+", query_lower)) - {"", "的", "了", "是", "在", "有", "和", "就", "不", "也", "都", "要", "会", "能", "这", "那"}
                content_terms = set(re.split(r"\W+", content_lower + " " + desc_lower))
                overlap = len(query_terms & content_terms)
                if overlap > 0:
                    score = min(overlap / max(len(query_terms), 1) * 0.6, 0.59)
            if score > 0:
                results.append((entry, score))
        results.sort(key=lambda r: r[1], reverse=True)
        return results[:limit]

    def get_stats(self) -> dict[str, int]:
        """获取各类记忆的数量统计。"""
        entries = self.list_all()
        stats: dict[str, int] = {"total": len(entries)}
        for entry in entries:
            stats[entry.memory_type] = stats.get(entry.memory_type, 0) + 1
        return stats

    def _ensure_dirs(self) -> None:
        """确保记忆目录存在。"""
        self._dir.mkdir(parents=True, exist_ok=True)
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_files(self) -> list[Path]:
        """列出所有会话文件。"""
        if not self._sessions_dir.exists():
            return []
        return sorted(self._sessions_dir.glob("*.md"))

    def _update_index(self, entry: MemoryEntry, file_path: Path) -> None:
        """追加一条记忆到 MEMORY.md 索引。"""
        self._ensure_dirs()
        rel_path = file_path.relative_to(self._dir)
        line = f"- [{entry.name}]({rel_path}) — {entry.description}\n"

        if self._index_path.exists():
            content = self._index_path.read_text(encoding="utf-8")
            if entry.name not in content:
                content = content.rstrip("\n") + "\n" + line
                self._index_path.write_text(content, encoding="utf-8")
        else:
            self._index_path.write_text("# Memory Index\n\n" + line, encoding="utf-8")
