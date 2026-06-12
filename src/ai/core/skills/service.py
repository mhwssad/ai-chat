"""Skill 服务 — 技能发现和索引管理的纯协调器（纯文件系统驱动）。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.ai.config.logging_setup import get_logger
from src.ai.core.skills.loader import SkillLoader
from src.ai.core.skills.matcher import SkillMatcher
from src.ai.core.skills.types import SkillIndex

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class SkillService:
    """技能索引服务。

    纯协调器，组合 Loader、Matcher 两个组件，
    提供缓存管理和索引查询的统一入口。
    不依赖任何外部子系统（tools、storage、callbacks）。

    AI 通过上下文中的索引判定需要某技能时，
    使用文件读取工具直接读取对应 SKILL.md 完整内容。
    """

    def __init__(
        self,
        *,
        loader: SkillLoader,
        matcher: SkillMatcher,
    ) -> None:
        self._loader = loader
        self._matcher = matcher
        self._cache: dict[str, SkillIndex] | None = None

    # ── 发现和缓存 ──────────────────────────────────────────

    def discover(self) -> list[SkillIndex]:
        """扫描文件系统，仅读取 frontmatter 建立索引。"""
        if self._cache is not None:
            return list(self._cache.values())
        self._cache = self._loader.discover()
        return list(self._cache.values())

    def get(self, name: str) -> SkillIndex | None:
        """按 name 获取单个技能索引。"""
        self.discover()
        if self._cache is None:
            return None
        return self._cache.get(name)

    def list_skills(self) -> list[SkillIndex]:
        """列出所有技能索引。"""
        return self.discover()

    def invalidate(self) -> None:
        """清除缓存，下次调用 discover 时重新扫描。"""
        self._cache = None

    # ── 匹配（委托 Matcher）─────────────────────────────────

    def match_slash_command(self, user_message: str) -> SkillIndex | None:
        """匹配用户消息中的斜杠命令。"""
        self.discover()
        if self._cache is None:
            return None
        return self._matcher.match_slash_command(user_message, self._cache)

    def get_slash_commands(self) -> list[dict[str, str]]:
        """列出所有用户可调用的斜杠命令。"""
        self.discover()
        if self._cache is None:
            return []
        return self._matcher.get_slash_commands(self._cache)

    def list_user_invocable(self) -> list[SkillIndex]:
        """列出所有用户可调用的技能（user_invocable=True）。"""
        self.discover()
        if self._cache is None:
            return []
        return self._matcher.list_user_invocable(self._cache)

    def list_auto_triggerable(self) -> list[SkillIndex]:
        """列出所有可自动触发的技能（disable_model_invocation=False）。"""
        self.discover()
        if self._cache is None:
            return []
        return self._matcher.list_auto_triggerable(self._cache)
