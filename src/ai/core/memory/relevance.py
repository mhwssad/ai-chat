"""相关记忆查找。"""

from __future__ import annotations

import re
from pathlib import Path

from .scanner import MemoryScanner
from .types import MemoryHeader, RelevantMemory


class MemoryRelevanceFinder:
    """基于关键词的轻量相关记忆查找。"""

    def __init__(self, scanner: MemoryScanner | None = None) -> None:
        self._scanner = scanner or MemoryScanner()

    def find(
        self,
        query: str,
        memory_dir: str | Path,
        *,
        recent_tools: list[str] | None = None,
        already_surfaced: set[str] | None = None,
        limit: int = 5,
    ) -> list[RelevantMemory]:
        headers = self._scanner.scan(memory_dir)
        already_surfaced = already_surfaced or set()
        scored: list[tuple[float, MemoryHeader]] = []
        for header in headers:
            if header.path in already_surfaced:
                continue
            score = self._score(query, header, recent_tools or [])
            if score > 0:
                scored.append((score, header))
        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[RelevantMemory] = []
        for score, header in scored[:limit]:
            results.append(
                RelevantMemory(
                    path=header.path,
                    memory_type=header.memory_type,
                    description=header.description,
                    score=score,
                    content=self._scanner.read_memory_file(header.path),
                )
            )
        return results

    def _score(self, query: str, header: MemoryHeader, recent_tools: list[str]) -> float:
        query_terms = set(tokenize(query))
        description_terms = set(tokenize(header.description))
        tool_terms = set(tokenize(" ".join(recent_tools)))
        if not query_terms:
            return 0.0
        overlap = len(query_terms & description_terms)
        tool_overlap = len(tool_terms & description_terms)
        age_bonus = 0.1
        return overlap + tool_overlap * 0.5 + age_bonus


def tokenize(text: str) -> list[str]:
    return [item for item in re.split(r"\W+", text.lower()) if item]

