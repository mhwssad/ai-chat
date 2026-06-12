"""统一的 frontmatter 解析工具。

支持两种文件格式：
- 单条目文件（向后兼容）：一个 frontmatter + 一段内容
- 会话文件（多条目）：文件头 frontmatter + 多个条目（每个条目有自己的 frontmatter）
"""

from src.ai.config.logging_setup import get_logger
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .types import MEMORY_TYPES, MemoryEntry

logger = get_logger(__name__)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, Any]:
    """解析简单 YAML frontmatter。"""
    data: dict[str, Any] = {}
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("\"'")
    return data


def _parse_entry(data: dict[str, Any], content: str, path: Path) -> MemoryEntry:
    """从 frontmatter 数据和内容构造 MemoryEntry。"""
    memory_type = data.get("type", "project")
    if memory_type not in MEMORY_TYPES:
        memory_type = "project"

    created_at_str = data.get("created_at", "")
    created_at: datetime | None = None
    if created_at_str:
        try:
            created_at = datetime.fromisoformat(created_at_str)
        except (ValueError, TypeError):
            pass

    return MemoryEntry(
        name=data.get("name", path.stem),
        memory_type=memory_type,  # type: ignore[arg-type]
        description=str(data.get("description") or path.stem),
        content=content,
        file_path=path,
        session_id=data.get("session_id"),
        scope=data.get("scope", "session" if data.get("session_id") else "project"),
        source_type=data.get("source_type", "manual"),
        source_id=data.get("source_id") or None,
        status=data.get("status", "active"),
        created_at=created_at or datetime.fromtimestamp(path.stat().st_mtime),
        metadata=data,
    )


def parse_memory_file(path: Path) -> MemoryEntry | None:
    """解析单条目记忆文件（向后兼容）。"""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    match = FRONTMATTER_RE.match(text)
    if match is None:
        return None

    data = parse_frontmatter(match.group(1))
    content = text[match.end() :].strip()
    return _parse_entry(data, content, path)


def parse_session_file(path: Path) -> list[MemoryEntry]:
    """解析会话文件（多条目）。

    文件格式：
    ---
    session_id: xxx
    updated_at: ...
    ---

    ---
    name: ...
    type: ...
    description: ...
    created_at: ...
    ---

    内容1

    ---
    name: ...
    type: ...
    description: ...
    created_at: ...
    ---

    内容2
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    # 按 --- 分割所有 frontmatter 块
    # 正则匹配所有 ---\n...\n--- 块
    blocks = list(FRONTMATTER_RE.finditer(text))
    if not blocks:
        return []

    # 第一个块是文件头（session_id, updated_at），跳过
    # 后续每个块是一个条目的 frontmatter
    entries: list[MemoryEntry] = []
    for i, match in enumerate(blocks):
        if i == 0:
            # 文件头，提取 session_id
            continue

        data = parse_frontmatter(match.group(1))

        # 条目内容是当前 frontmatter 结束到下一个 frontmatter 开始之间的文本
        content_start = match.end()
        if i + 1 < len(blocks):
            content_end = blocks[i + 1].start()
        else:
            content_end = len(text)

        content = text[content_start:content_end].strip()

        entry = _parse_entry(data, content, path)
        entries.append(entry)

    return entries


def format_session_file(session_id: str, entries: list[MemoryEntry]) -> str:
    """格式化会话文件内容。"""
    now = datetime.now().isoformat()
    lines = [
        "---",
        f"session_id: {session_id}",
        f"updated_at: {now}",
        "---",
        "",
    ]

    for entry in entries:
        created: str = (
            entry.created_at.isoformat()
            if isinstance(entry.created_at, datetime)
            else (entry.created_at or now)
        )
        lines.extend(
            [
                "---",
                f"name: {entry.name}",
                f"type: {entry.memory_type}",
                f"description: {entry.description}",
                f"scope: {entry.scope}",
                f"source_type: {entry.source_type}",
                f"status: {entry.status}",
                f"created_at: {created}",
                "---",
                "",
                entry.content.strip(),
                "",
            ]
        )

    return "\n".join(lines)


def format_entry_append(entry: MemoryEntry) -> str:
    """格式化单个条目（用于追加到已有文件）。"""
    created_dt = entry.created_at or datetime.now()
    created_str: str = (
        created_dt.isoformat() if isinstance(created_dt, datetime) else created_dt
    )
    return (
        "---\n"
        f"name: {entry.name}\n"
        f"type: {entry.memory_type}\n"
        f"description: {entry.description}\n"
        f"scope: {entry.scope}\n"
        f"source_type: {entry.source_type}\n"
        f"status: {entry.status}\n"
        f"created_at: {created_str}\n"
        "---\n\n"
        f"{entry.content.strip()}\n"
    )
