"""记忆核心服务。"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from src.ai.storage import MemoryEntry, MemoryEntryRepository, get_session

from .paths import MemoryPathResolver
from .prompt import MemoryPromptBuilder
from .relevance import MemoryRelevanceFinder
from .scanner import MemoryScanner
from .types import MemoryType, MemoryWriteRequest, RelevantMemory


class MemoryService:
    """统一记忆入口。"""

    def __init__(
        self,
        *,
        path_resolver: MemoryPathResolver | None = None,
        scanner: MemoryScanner | None = None,
        relevance_finder: MemoryRelevanceFinder | None = None,
        prompt_builder: MemoryPromptBuilder | None = None,
    ) -> None:
        self._paths = path_resolver or MemoryPathResolver()
        self._scanner = scanner or MemoryScanner()
        self._relevance = relevance_finder or MemoryRelevanceFinder(self._scanner)
        self._prompt = prompt_builder or MemoryPromptBuilder(self._scanner)

    def auto_memory_dir(self) -> Path:
        return self._paths.auto_memory_dir()

    def load_prompt(self, *, display_name: str = "Project") -> str:
        memory_dir = self.auto_memory_dir()
        return self._prompt.build(display_name=display_name, memory_dir=memory_dir)

    def find_relevant(
        self,
        query: str,
        *,
        limit: int = 5,
        already_surfaced: set[str] | None = None,
    ) -> list[RelevantMemory]:
        return self._relevance.find(
            query,
            self.auto_memory_dir(),
            already_surfaced=already_surfaced,
            limit=limit,
        )

    def write_memory(self, request: MemoryWriteRequest) -> MemoryEntry:
        memory_dir = self.auto_memory_dir()
        memory_dir.mkdir(parents=True, exist_ok=True)
        path = self._memory_file_path(memory_dir, request.memory_type, request.description, request.content)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._format_memory_file(request), encoding="utf-8")
        with get_session() as session:
            return MemoryEntryRepository(session).create(
                session_id=request.session_id,
                scope=request.scope,
                memory_type=request.memory_type,
                source_type=request.source_type,
                source_id=request.source_id,
                content_summary=request.description or request.content[:200],
                content_ref=str(path),
                status="active",
            )

    def list_entries(self, *, scope: str | None = None, limit: int = 100) -> list[MemoryEntry]:
        with get_session() as session:
            return MemoryEntryRepository(session).get_active(scope=scope, limit=limit)

    def disable_entry(self, entry_id: int) -> MemoryEntry | None:
        with get_session() as session:
            repo = MemoryEntryRepository(session)
            entry = repo.get_by_id(entry_id)
            if entry is None:
                return None
            return repo.update(entry, status="disabled")

    def extract_candidates(self, text: str) -> list[MemoryWriteRequest]:
        """预留自动提取入口。第一版只返回空列表。"""
        return []

    def _memory_file_path(self, memory_dir: Path, memory_type: MemoryType, description: str, content: str) -> Path:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
        title = _slug(description or content[:40])
        return memory_dir / memory_type / f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{title}-{digest}.md"

    def _format_memory_file(self, request: MemoryWriteRequest) -> str:
        description = request.description or request.content[:120].replace("\n", " ")
        return (
            "---\n"
            f"type: {request.memory_type}\n"
            f"description: {description}\n"
            "---\n\n"
            f"{request.content.strip()}\n"
        )


def _slug(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in value.lower()).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned[:48] or "memory"


memory_service = MemoryService()
