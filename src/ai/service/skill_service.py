"""技能 API 服务 — SkillService 的薄包装。

共享服务层，CLI 和 API 路由统一使用。
"""

from __future__ import annotations

from dataclasses import asdict
from src.ai.config.logging_setup import get_logger
from typing import Any

logger = get_logger(__name__)


class SkillApiService:
    """技能 API 服务。

    职责：
    1. 技能发现和列表
    2. 技能详情查询
    3. 斜杠命令查询
    """

    def __init__(self, *, skill_service: Any) -> None:
        self._svc = skill_service

    def discover(self) -> list[dict[str, Any]]:
        """重新发现技能。

        Returns:
            技能索引列表。
        """
        skills = self._svc.discover()
        return [asdict(s) for s in skills]

    def list_skills(self) -> list[dict[str, Any]]:
        """列出所有技能。

        Returns:
            技能索引列表。
        """
        skills = self._svc.list_skills()
        return [asdict(s) for s in skills]

    def get_skill(self, name: str) -> dict[str, Any] | None:
        """获取指定技能。

        Args:
            name: 技能名称。

        Returns:
            技能信息字典，不存在返回 None。
        """
        skill = self._svc.get(name)
        if skill is None:
            return None
        return asdict(skill)

    def get_slash_commands(self) -> list[dict[str, str]]:
        """获取可用的斜杠命令列表。

        Returns:
            命令列表（name + description）。
        """
        return self._svc.get_slash_commands()

    def list_user_invocable(self) -> list[dict[str, Any]]:
        """列出用户可调用的技能。

        Returns:
            技能索引列表。
        """
        skills = self._svc.list_user_invocable()
        return [asdict(s) for s in skills]
