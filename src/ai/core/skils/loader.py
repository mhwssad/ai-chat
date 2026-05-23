"""Skill 文件加载。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.ai.config.base_config import project_root

from .errors import SkillLoadError
from .types import SkillDefinition


class SkillLoader:
    """扫描和解析本地 SKILL.md。"""

    def __init__(self, *, base_dirs: list[str | Path] | None = None) -> None:
        self._base_dirs = [Path(item) for item in base_dirs] if base_dirs else [
            project_root / "skills",
            project_root / "data" / "skills",
            project_root / "src" / "ai" / "core" / "skils" / "skills",
        ]

    def discover(self) -> list[SkillDefinition]:
        skills: list[SkillDefinition] = []
        for base_dir in self._base_dirs:
            if not base_dir.exists():
                continue
            for path in base_dir.rglob("SKILL.md"):
                skills.append(self.load(path))
        return skills

    def load(self, path: str | Path) -> SkillDefinition:
        skill_path = Path(path)
        if not skill_path.exists():
            raise SkillLoadError("Skill 文件不存在", context={"path": str(skill_path)})
        text = skill_path.read_text(encoding="utf-8")
        metadata, body = split_frontmatter(text)
        skill_key = str(metadata.get("name") or skill_path.parent.name)
        description = str(metadata.get("description") or body.splitlines()[0] if body.splitlines() else skill_key)
        capabilities = metadata.get("capabilities") or []
        if isinstance(capabilities, str):
            capabilities = [capabilities]
        input_schema = metadata.get("input_schema") or metadata.get("inputSchema") or {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "传给 skill 的用户输入或任务上下文"}
            },
        }
        return SkillDefinition(
            skill_key=skill_key,
            display_name=metadata.get("display_name") or metadata.get("title"),
            description=description,
            version=metadata.get("version"),
            source_path=skill_path.resolve(),
            prompt=body.strip(),
            capabilities=[str(item) for item in capabilities],
            input_schema=input_schema,
            metadata={key: value for key, value in metadata.items() if key not in {"name", "description", "version", "capabilities", "input_schema", "inputSchema"}},
        )


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """解析 Markdown frontmatter。"""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        metadata = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        raise SkillLoadError("Skill frontmatter 解析失败", context={"error": str(exc)}) from exc
    if not isinstance(metadata, dict):
        metadata = {}
    return metadata, parts[2]

