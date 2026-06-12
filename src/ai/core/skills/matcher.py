"""Skill 斜杠命令匹配与过滤查询。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.ai.core.skills.types import SkillIndex

if TYPE_CHECKING:
    pass


class SkillMatcher:
    """技能匹配器。

    负责斜杠命令解析和技能过滤查询，
    从已缓存的 SkillIndex 集合中筛选符合条件的技能。
    """

    def match_slash_command(
        self, user_message: str, skills: dict[str, SkillIndex]
    ) -> SkillIndex | None:
        """匹配用户消息中的斜杠命令。

        Args:
            user_message: 用户原始输入。
            skills: 当前已发现的技能字典（name → index）。

        Returns:
            匹配到的 SkillIndex，无匹配返回 None。
        """
        user_message = user_message.strip()
        if not user_message.startswith("/"):
            return None
        command = user_message.split()[0][1:]
        if not command:
            return None
        index = skills.get(command)
        if index is not None and index.user_invocable:
            return index
        return None

    def get_slash_commands(
        self, skills: dict[str, SkillIndex]
    ) -> list[dict[str, str]]:
        """列出所有用户可调用的斜杠命令。

        Args:
            skills: 当前已发现的技能字典。

        Returns:
            包含 command 和 description 的字典列表。
        """
        return [
            {"command": f"/{idx.name}", "description": idx.description}
            for idx in skills.values()
            if idx.user_invocable
        ]

    def list_user_invocable(
        self, skills: dict[str, SkillIndex]
    ) -> list[SkillIndex]:
        """列出所有用户可调用的技能。

        Args:
            skills: 当前已发现的技能字典。

        Returns:
            user_invocable=True 的技能列表。
        """
        return [idx for idx in skills.values() if idx.user_invocable]

    def list_auto_triggerable(
        self, skills: dict[str, SkillIndex]
    ) -> list[SkillIndex]:
        """列出所有可自动触发的技能。

        Args:
            skills: 当前已发现的技能字典。

        Returns:
            disable_model_invocation=False 的技能列表。
        """
        return [
            idx for idx in skills.values() if not idx.disable_model_invocation
        ]
