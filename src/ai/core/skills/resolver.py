"""Skill 支持文件访问 — references/ 和 scripts/ 目录操作。"""

import logging
from pathlib import Path

from src.ai.exception.skill_exception import SkillError

logger = logging.getLogger(__name__)


class SkillResolver:
    """技能支持文件解析器。

    负责访问技能目录下的 references/ 和 scripts/ 子目录，
    提供文件列举和内容加载能力（Level 3 渐进式披露）。
    """

    def list_references(self, skill_dir: Path) -> list[str]:
        """列出 references/ 目录中的文件名。

        Args:
            skill_dir: 技能根目录路径。

        Returns:
            文件名列表（仅文件，已排序）。
        """
        ref_dir = skill_dir / "references"
        if not ref_dir.is_dir():
            return []
        return [f.name for f in sorted(ref_dir.iterdir()) if f.is_file()]

    def load_reference(self, skill_dir: Path, filename: str) -> str:
        """加载 references/ 目录中的文件内容。

        Args:
            skill_dir: 技能根目录路径。
            filename: 目标文件名。

        Returns:
            文件文本内容。

        Raises:
            SkillError: 文件不存在或读取失败。
        """
        ref_path = skill_dir / "references" / filename
        if not ref_path.is_file():
            raise SkillError(
                f"参考文件不存在: {filename}",
                context={"filename": filename},
            )
        try:
            return ref_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SkillError(
                f"读取参考文件失败: {filename}",
                context={"filename": filename, "error": str(exc)},
            ) from exc

    def list_scripts(self, skill_dir: Path) -> list[str]:
        """列出 scripts/ 目录中的文件名。

        Args:
            skill_dir: 技能根目录路径。

        Returns:
            文件名列表（仅文件，已排序）。
        """
        script_dir = skill_dir / "scripts"
        if not script_dir.is_dir():
            return []
        return [f.name for f in sorted(script_dir.iterdir()) if f.is_file()]
