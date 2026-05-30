"""Skill 服务 — 技能发现、激活、匹配的核心协调器（纯文件系统驱动）。"""

import logging

from src.ai.core.skills.loader import SkillLoader
from src.ai.core.skills.matcher import SkillMatcher
from src.ai.core.skills.renderer import SkillRenderer
from src.ai.core.skills.resolver import SkillResolver
from src.ai.core.skills.types import SkillDefinition, SkillMetadata
from src.ai.exception.skill_exception import SkillNotFoundError

logger = logging.getLogger(__name__)


class SkillService:
    """技能上下文注入服务。

    作为协调器，组合 Loader、Renderer、Resolver、Matcher 四个组件，
    提供缓存管理和渐进式披露（3-level）的统一入口。
    """

    def __init__(
        self,
        *,
        loader: SkillLoader,
        renderer: SkillRenderer,
        resolver: SkillResolver,
        matcher: SkillMatcher,
    ) -> None:
        self._loader = loader
        self._renderer = renderer
        self._resolver = resolver
        self._matcher = matcher
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

    # ── 工具注册 ──────────────────────────────────────────────

    def register_tools(self, registry) -> None:
        """将技能工具注册到工具注册表。

        Args:
            registry: 工具注册表实例。
        """
        from src.ai.core.skills.tools import register_skill_tools

        register_skill_tools(registry, self)

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
            raise SkillNotFoundError(f"技能不存在: {name}", context={"name": name})
        return self._renderer.render(
            defn.instruction_template,
            arguments=arguments,
        )

    # ── 支持文件（委托 Resolver）─────────────────────────────

    def list_references(self, name: str) -> list[str]:
        """列出技能的 references/ 目录中的文件。"""
        defn = self._require(name)
        return self._resolver.list_references(defn.skill_dir)

    def load_reference(self, name: str, filename: str) -> str:
        """Level 3: 加载技能的 references/ 目录中的文件内容。"""
        defn = self._require(name)
        return self._resolver.load_reference(defn.skill_dir, filename)

    def list_scripts(self, name: str) -> list[str]:
        """列出技能的 scripts/ 目录中的文件。"""
        defn = self._require(name)
        return self._resolver.list_scripts(defn.skill_dir)

    # ── 匹配（委托 Matcher）─────────────────────────────────

    def match_slash_command(self, user_message: str) -> SkillDefinition | None:
        """匹配用户消息中的斜杠命令。"""
        self.discover()
        assert self._cache is not None
        return self._matcher.match_slash_command(user_message, self._cache)

    def get_slash_commands(self) -> list[dict[str, str]]:
        """列出所有用户可调用的斜杠命令。"""
        self.discover()
        assert self._cache is not None
        return self._matcher.get_slash_commands(self._cache)

    def list_user_invocable(self) -> list[SkillDefinition]:
        """列出所有用户可调用的技能（user_invocable=True）。"""
        self.discover()
        assert self._cache is not None
        return self._matcher.list_user_invocable(self._cache)

    def list_auto_triggerable(self) -> list[SkillDefinition]:
        """列出所有可自动触发的技能（disable_model_invocation=False）。"""
        self.discover()
        assert self._cache is not None
        return self._matcher.list_auto_triggerable(self._cache)

    # ── 内部辅助 ────────────────────────────────────────────

    def _require(self, name: str) -> SkillDefinition:
        """获取技能，不存在则抛出 SkillNotFoundError。"""
        defn = self.get(name)
        if defn is None:
            raise SkillNotFoundError(f"技能不存在: {name}", context={"name": name})
        return defn
