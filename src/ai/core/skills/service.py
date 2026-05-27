"""Skill 服务 — 技能发现、激活、匹配的核心协调器（纯文件系统驱动）。"""

import logging

from src.ai.core.skills.loader import SkillLoader
from src.ai.core.skills.renderer import SkillRenderer
from src.ai.core.skills.types import SkillDefinition, SkillMetadata
from src.ai.exception.skill_exception import SkillError, SkillNotFoundError

logger = logging.getLogger(__name__)


class SkillService:
    """技能上下文注入服务。"""

    def __init__(self, *, loader: SkillLoader | None = None) -> None:
        self._loader = loader or SkillLoader()
        self._renderer = SkillRenderer()
        self._cache: dict[str, SkillDefinition] | None = None

    # ── 发现和缓存 ──────────────────────────────────────────

    def discover(self) -> list[SkillDefinition]:
        """扫描文件系统，解析 SKILL.md，缓存到内存。"""
        if self._cache is not None:
            return list(self._cache.values())
        self._cache = self._loader.discover()
        return list(self._cache.values())

    def get(self, name: str) -> SkillDefinition | None:
        """按 name 获取单个技能定义。"""
        self.discover()
        assert self._cache is not None
        return self._cache.get(name)

    def list_skills(self) -> list[SkillDefinition]:
        """列出所有技能。"""
        return self.discover()

    def invalidate(self) -> None:
        """清除缓存，下次调用 discover 时重新扫描。"""
        self._cache = None

    # ── 渐进式披露 ──────────────────────────────────────────

    def get_skill_metadata(self) -> list[SkillMetadata]:
        """Level 1: 返回所有技能的元数据（用于注入 LLM 上下文）。

        仅包含 name + description，约 100 tokens/技能。
        """
        return [
            SkillMetadata(
                name=d.name,
                description=d.description,
                argument_hint=d.argument_hint,
                disable_model_invocation=d.disable_model_invocation,
                user_invocable=d.user_invocable,
            )
            for d in self.discover()
        ]

    # ── 激活 ────────────────────────────────────────────────

    def activate(self, name: str, *, arguments: str = "") -> str:
        """Level 2: 激活技能，渲染完整指令内容。

        Args:
            name: 技能名称。
            arguments: 用户输入参数（用于 $ARGUMENTS 替换）。

        Returns:
            渲染后的指令内容。
        """
        defn = self.get(name)
        if defn is None:
            raise SkillNotFoundError(
                f"技能不存在: {name}", context={"name": name}
            )
        return self._renderer.render(
            defn.instruction_template, arguments=arguments,
        )

    # ── 支持文件 ────────────────────────────────────────────

    def list_references(self, name: str) -> list[str]:
        """列出技能的 references/ 目录中的文件。"""
        defn = self.get(name)
        if defn is None:
            raise SkillNotFoundError(f"技能不存在: {name}", context={"name": name})
        ref_dir = defn.skill_dir / "references"
        if not ref_dir.is_dir():
            return []
        return [f.name for f in sorted(ref_dir.iterdir()) if f.is_file()]

    def load_reference(self, name: str, filename: str) -> str:
        """Level 3: 加载技能的 references/ 目录中的文件内容。"""
        defn = self.get(name)
        if defn is None:
            raise SkillNotFoundError(f"技能不存在: {name}", context={"name": name})
        ref_path = defn.skill_dir / "references" / filename
        if not ref_path.is_file():
            raise SkillError(
                f"参考文件不存在: {filename}",
                context={"name": name, "filename": filename},
            )
        try:
            return ref_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SkillError(
                f"读取参考文件失败: {filename}",
                context={"name": name, "filename": filename, "error": str(exc)},
            ) from exc

    def list_scripts(self, name: str) -> list[str]:
        """列出技能的 scripts/ 目录中的文件。"""
        defn = self.get(name)
        if defn is None:
            raise SkillNotFoundError(f"技能不存在: {name}", context={"name": name})
        script_dir = defn.skill_dir / "scripts"
        if not script_dir.is_dir():
            return []
        return [f.name for f in sorted(script_dir.iterdir()) if f.is_file()]

    # ── 匹配 ────────────────────────────────────────────────

    def match_slash_command(self, user_message: str) -> SkillDefinition | None:
        """匹配用户消息中的斜杠命令。"""
        user_message = user_message.strip()
        if not user_message.startswith("/"):
            return None
        command = user_message.split()[0][1:]
        if not command:
            return None
        for defn in self.discover():
            if defn.user_invocable and defn.name == command:
                return defn
        return None

    def get_slash_commands(self) -> list[dict[str, str]]:
        """列出所有用户可调用的斜杠命令。"""
        return [
            {"command": f"/{d.name}", "description": d.description}
            for d in self.discover()
            if d.user_invocable
        ]

    def list_user_invocable(self) -> list[SkillDefinition]:
        """列出所有用户可调用的技能（user_invocable=True）。"""
        return [d for d in self.discover() if d.user_invocable]

    def list_auto_triggerable(self) -> list[SkillDefinition]:
        """列出所有可自动触发的技能（disable_model_invocation=False）。"""
        return [d for d in self.discover() if d.is_auto_triggerable]


skill_service = SkillService()
