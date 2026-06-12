"""Skill 文件发现和加载 — Agent Skills 开放标准。

启动阶段仅扫描 YAML frontmatter，构建轻量索引。
完整内容由 AI 按需通过文件路径读取。
"""

import re
from pathlib import Path
from typing import Any

import yaml

from src.ai.config.base_config import project_root
from src.ai.config.logging_setup import get_logger
from src.ai.config.container import config
from src.ai.core.skills.types import SkillIndex
from src.ai.exception.skill_exception import SkillLoadError

logger = get_logger(__name__)

# frontmatter 分隔符正则
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """将 SKILL.md 内容分割为 YAML frontmatter 和正文。

    Args:
        text: 完整的文件内容。

    Returns:
        (frontmatter_dict, body) 元组。
    """
    match = _FRONTMATTER_RE.match(text)
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
    """扫描配置目录，解析 SKILL.md frontmatter，返回 SkillIndex 字典。

    仅读取 name、description 等控制匹配/注入行为的最小字段。
    其余 frontmatter 字段（model, context, agent, allowed-tools 等）
    由 AI 激活时从原始内容自行解读。
    """

    def __init__(self, *, base_dirs: list[str | Path] | None = None) -> None:
        self._base_dirs = self._resolve_dirs(base_dirs)

    @staticmethod
    def _resolve_dirs(base_dirs: list[str | Path] | None) -> list[Path]:
        """解析技能目录列表。"""
        if base_dirs:
            return [Path(d) for d in base_dirs]

        configured = config.settings.skills.skill_dirs
        if configured:
            return [Path(d.strip()) for d in configured.split(",") if d.strip()]

        defaults = [
            Path.home() / ".ai-chat" / "skills",
            project_root / "data" / "skills",
            project_root / "skills",
        ]
        return defaults

    def discover(self) -> dict[str, SkillIndex]:
        """扫描所有目录，仅读取 frontmatter 建立索引。

        同名 name 后出现的覆盖先出现的。

        Returns:
            dict[str, SkillIndex] 按 name 索引。
        """
        result: dict[str, SkillIndex] = {}
        for base_dir in self._base_dirs:
            if not base_dir.is_dir():
                continue
            for skill_dir in sorted(base_dir.iterdir()):
                if not skill_dir.is_dir():
                    continue
                skill_file = skill_dir / "SKILL.md"
                if skill_file.is_file():
                    try:
                        index = self._scan_frontmatter(skill_file)
                        result[index.name] = index
                    except SkillLoadError:
                        logger.warning(
                            "跳过无效技能: %s", skill_file, exc_info=True
                        )
        return result

    def _scan_frontmatter(self, path: Path) -> SkillIndex:
        """扫描单个 SKILL.md 的 frontmatter，构建索引条目。

        Args:
            path: SKILL.md 文件路径。

        Returns:
            仅含元数据的 SkillIndex。

        Raises:
            SkillLoadError: 文件无法读取或格式错误。
        """
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SkillLoadError(
                f"无法读取技能文件: {path}", context={"error": str(exc)}
            ) from exc

        meta, _body = split_frontmatter(text)
        if not meta.get("name"):
            raise SkillLoadError(f"技能缺少 name 字段: {path}")

        return SkillIndex(
            name=str(meta["name"]),
            description=str(meta.get("description", "")),
            source_path=path,
            disable_model_invocation=bool(
                meta.get("disable-model-invocation", False)
            ),
            user_invocable=bool(
                meta.get("user-invocable", meta.get("user_invocable", True))
            ),
            argument_hint=meta.get("argument-hint") or meta.get("argument_hint"),
        )
