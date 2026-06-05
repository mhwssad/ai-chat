"""Skill 服务 — 技能发现、激活、匹配的核心协调器（纯文件系统驱动）。"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING

from sqlmodel import Session

from src.ai.core.callbacks.audit import AuditEvent, record_audit_event
from src.ai.core.skills.loader import SkillLoader
from src.ai.core.skills.matcher import SkillMatcher
from src.ai.core.skills.renderer import SkillRenderer
from src.ai.core.skills.resolver import SkillResolver
from src.ai.core.skills.types import SkillDefinition, SkillMetadata
from src.ai.core.tools.types import ToolPlugin
from src.ai.exception.skill_exception import SkillNotFoundError
from src.ai.storage.config_repository import SkillConfigRepository

if TYPE_CHECKING:
    from src.ai.core.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class SkillService(ToolPlugin):
    """技能上下文注入服务。

    作为协调器，组合 Loader、Renderer、Resolver、Matcher 四个组件，
    提供缓存管理和渐进式披露（3-level）的统一入口。
    实现 ToolPlugin 接口，支持自动注册技能工具。
    """

    def __init__(
        self,
        *,
        loader: SkillLoader,
        renderer: SkillRenderer,
        resolver: SkillResolver,
        matcher: SkillMatcher,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        self._loader = loader
        self._renderer = renderer
        self._resolver = resolver
        self._matcher = matcher
        self._session_factory = session_factory
        self._cache: dict[str, SkillDefinition] | None = None

    # ── 发现和缓存 ──────────────────────────────────────────

    def discover(self) -> list[SkillDefinition]:
        """扫描文件系统，解析 SKILL.md，同步并合并数据库状态。"""
        if self._cache is not None:
            return list(self._cache.values())
        discovered = self._loader.discover()
        self._sync_discovered(discovered)
        self._cache = self._apply_persisted_state(discovered)
        return list(self._cache.values())

    def get(self, name: str) -> SkillDefinition | None:
        """按 name 获取单个技能定义。"""
        self.discover()
        if self._cache is None:
            return None
        return self._cache.get(name)

    def list_skills(self) -> list[SkillDefinition]:
        """列出所有技能。"""
        return self.discover()

    def set_enabled(self, name: str, enabled: bool) -> SkillDefinition:
        """设置技能启用状态并刷新缓存。"""
        self.discover()
        if self._cache is None or name not in self._cache:
            raise SkillNotFoundError(f"技能不存在: {name}", context={"name": name})

        if self._session_factory is not None:
            with self._session_factory() as session:
                repo = SkillConfigRepository(session)
                record = repo.get_by_key(name)
                if record is not None:
                    repo.update(record, enabled=enabled)
                session.commit()

        self.invalidate()
        defn = self.get(name)
        if defn is None:
            raise SkillNotFoundError(f"技能不存在: {name}", context={"name": name})
        record_audit_event(
            AuditEvent(
                event_type="skill_state_change",
                source_module="skills",
                target=name,
                input_summary=json.dumps({"enabled": enabled}, ensure_ascii=False),
                status="success",
            )
        )
        return defn

    def enable(self, name: str) -> SkillDefinition:
        """启用技能。"""
        return self.set_enabled(name, True)

    def disable(self, name: str) -> SkillDefinition:
        """禁用技能。"""
        return self.set_enabled(name, False)

    def invalidate(self) -> None:
        """清除缓存，下次调用 discover 时重新扫描。"""
        self._cache = None

    # ── 工具注册 ──────────────────────────────────────────────

    def register_tools(self, registry: ToolRegistry) -> None:
        """将技能工具注册到工具注册表。

        实现 ToolPlugin 接口，由 ToolManager 在加载内置工具时调用。

        Args:
            registry: ToolRegistry 实例。
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
                enabled=d.enabled,
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
        if not defn.enabled:
            record_audit_event(
                AuditEvent(
                    event_type="skill_activate",
                    source_module="skills",
                    target=name,
                    input_summary=arguments,
                    status="denied",
                    error_type="SkillDisabled",
                    error_message="技能已禁用",
                )
            )
            raise SkillNotFoundError(f"技能已禁用: {name}", context={"name": name})
        content = self._renderer.render(
            defn.instruction_template,
            arguments=arguments,
        )
        record_audit_event(
            AuditEvent(
                event_type="skill_activate",
                source_module="skills",
                target=name,
                input_summary=arguments,
                output_summary=f"渲染字符数={len(content)}",
                status="success",
            )
        )
        return content

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
        if self._cache is None:
            return None
        return self._matcher.match_slash_command(user_message, self._cache)

    def get_slash_commands(self) -> list[dict[str, str]]:
        """列出所有用户可调用的斜杠命令。"""
        self.discover()
        if self._cache is None:
            return []
        return self._matcher.get_slash_commands(self._cache)

    def list_user_invocable(self) -> list[SkillDefinition]:
        """列出所有用户可调用的技能（user_invocable=True）。"""
        self.discover()
        if self._cache is None:
            return []
        return self._matcher.list_user_invocable(self._cache)

    def list_auto_triggerable(self) -> list[SkillDefinition]:
        """列出所有可自动触发的技能（disable_model_invocation=False）。"""
        self.discover()
        if self._cache is None:
            return []
        return self._matcher.list_auto_triggerable(self._cache)

    # ── 内部辅助 ────────────────────────────────────────────

    def _require(self, name: str) -> SkillDefinition:
        """获取技能，不存在则抛出 SkillNotFoundError。"""
        defn = self.get(name)
        if defn is None:
            raise SkillNotFoundError(f"技能不存在: {name}", context={"name": name})
        if not defn.enabled:
            raise SkillNotFoundError(f"技能已禁用: {name}", context={"name": name})
        return defn

    def _sync_discovered(self, discovered: dict[str, SkillDefinition]) -> None:
        """将文件系统发现到的技能基础信息同步到配置表。"""
        if self._session_factory is None:
            return

        try:
            with self._session_factory() as session:
                repo = SkillConfigRepository(session)
                for defn in discovered.values():
                    record = repo.get_by_key(defn.name)
                    payload = {
                        "display_name": defn.name,
                        "description": defn.description,
                        "source_path": str(defn.source_path),
                        "user_invocable": defn.user_invocable,
                        "disable_model_invocation": defn.disable_model_invocation,
                        "allowed_tools_json": json.dumps(
                            defn.allowed_tools,
                            ensure_ascii=False,
                        ),
                        "extra": json.dumps(
                            {
                                "argument_hint": defn.argument_hint,
                                "model": defn.model,
                                "context_fork": defn.context_fork,
                                "agent_type": defn.agent_type,
                            },
                            ensure_ascii=False,
                        ),
                    }
                    if record is None:
                        repo.create(skill_key=defn.name, enabled=True, **payload)
                    else:
                        repo.update(record, **payload)
                session.commit()
        except Exception:
            logger.debug("同步技能配置失败，继续使用文件系统视图", exc_info=True)

    def _apply_persisted_state(
        self, discovered: dict[str, SkillDefinition]
    ) -> dict[str, SkillDefinition]:
        """将数据库启停状态合并到技能定义。"""
        if self._session_factory is None:
            return discovered

        try:
            with self._session_factory() as session:
                repo = SkillConfigRepository(session)
                rows = repo.list(limit=1000, order_by="skill_key", descending=False)
        except Exception:
            logger.debug("读取技能配置失败，继续使用文件系统视图", exc_info=True)
            return discovered

        state = {row.skill_key: row for row in rows}
        merged: dict[str, SkillDefinition] = {}
        for name, defn in discovered.items():
            row = state.get(name)
            merged[name] = replace(defn, enabled=row.enabled if row else True)
        return merged
