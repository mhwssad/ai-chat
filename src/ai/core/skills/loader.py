"""Skill 文件发现和加载 — Agent Skills 开放标准。"""

import logging
import re
from pathlib import Path
from typing import Any

import yaml

from src.ai.config.base_config import project_root
from src.ai.config.settings import settings
from src.ai.core.skills.types import SkillDefinition
from src.ai.exception.skill_exception import SkillLoadError

logger = logging.getLogger(__name__)


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """将 SKILL.md 内容分割为 YAML frontmatter 和正文。

    Args:
        text: 完整的文件内容。

    Returns:
        (frontmatter_dict, body) 元组。
    """
    pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)
    match = pattern.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise SkillLoadError(
            "YAML frontmatter 解析失败", context={"error": str(exc)}
        ) from exc
    body = match.group(2).strip()
    return meta, body


class SkillLoader:
    """扫描配置目录，解析 SKILL.md，返回 SkillDefinition 字典。"""

    def __init__(self, *, base_dirs: list[str | Path] | None = None) -> None:
        self._base_dirs = self._resolve_dirs(base_dirs)

    @staticmethod
    def _resolve_dirs(base_dirs: list[str | Path] | None) -> list[Path]:
        """解析技能目录列表。"""
        if base_dirs:
            return [Path(d) for d in base_dirs]

        configured = settings.skills.skill_dirs
        if configured:
            return [Path(d.strip()) for d in configured.split(",") if d.strip()]

        defaults = [
            Path.home() / ".ai-chat" / "skills",
            project_root / "data" / "skills",
            project_root / "skills",
        ]
        return defaults

    def discover(self) -> dict[str, SkillDefinition]:
        """扫描所有目录，同名 name 后出现的覆盖先出现的。

        Returns:
            dict[str, SkillDefinition] 按 name 索引。
        """
        result: dict[str, SkillDefinition] = {}
        for base_dir in self._base_dirs:
            if not base_dir.is_dir():
                continue
            for skill_dir in sorted(base_dir.iterdir()):
                if not skill_dir.is_dir():
                    continue
                skill_file = skill_dir / "SKILL.md"
                if skill_file.is_file():
                    try:
                        defn = self.load(skill_file)
                        result[defn.name] = defn
                    except SkillLoadError:
                        logger.warning("跳过无效技能: %s", skill_file, exc_info=True)
        return result

    def load(self, path: str | Path) -> SkillDefinition:
        """解析单个 SKILL.md 文件。

        Args:
            path: SKILL.md 文件路径。

        Returns:
            解析后的 SkillDefinition。

        Raises:
            SkillLoadError: 文件无法读取或格式错误。
        """
        path = Path(path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SkillLoadError(
                f"无法读取技能文件: {path}", context={"error": str(exc)}
            ) from exc

        meta, body = split_frontmatter(text)
        if not meta.get("name"):
            raise SkillLoadError(f"技能缺少 name 字段: {path}")
        if not body.strip():
            raise SkillLoadError(f"技能指令模板为空: {path}")

        # 解析 allowed-tools（逗号分隔）
        allowed_tools_str = meta.get("allowed-tools", "")
        if isinstance(allowed_tools_str, list):
            allowed_tools = [str(t).strip() for t in allowed_tools_str if str(t).strip()]
        elif isinstance(allowed_tools_str, str) and allowed_tools_str:
            allowed_tools = [t.strip() for t in allowed_tools_str.split(",") if t.strip()]
        else:
            allowed_tools = []

        # 解析 context: fork
        context_val = str(meta.get("context", "")).lower().strip()
        context_fork = context_val == "fork"
        agent_type = meta.get("agent") if context_fork else None

        return SkillDefinition(
            name=str(meta["name"]),
            description=str(meta.get("description", "")),
            source_path=path,
            skill_dir=path.parent,
            instruction_template=body,
            disable_model_invocation=bool(meta.get("disable-model-invocation", False)),
            user_invocable=bool(meta.get("user-invocable", meta.get("user_invocable", True))),
            allowed_tools=allowed_tools,
            argument_hint=meta.get("argument-hint") or meta.get("argument_hint"),
            model=meta.get("model"),
            context_fork=context_fork,
            agent_type=str(agent_type) if agent_type else None,
        )
