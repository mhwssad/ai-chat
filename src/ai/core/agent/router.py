"""Agent 路由器 — 分析用户意图，分发给最合适的 Agent。"""

from __future__ import annotations

import json
import re
from typing import Any

from src.ai.config.logging_setup import get_logger
from src.ai.core.agent.roles import AgentProfile, AgentRole, DEFAULT_PROFILES

logger = get_logger(__name__)

# 路由系统提示词
_ROUTER_PROMPT = """\
分析以下用户请求，判断应该交给哪个专业 Agent 处理。

可用角色及其能力：
{role_descriptions}

请以严格的 JSON 格式回复，不要包含其他文字：
{{"role": "<角色名>", "confidence": 0.0, "reason": "<理由>"}}
"""


class AgentRouter:
    """Agent 路由器 — 分析用户意图，分发给最合适的 Agent。

    路由策略：
    1. 关键词匹配（快速路径）：检测用户消息中的关键词直接路由
    2. LLM 路由（精确路径）：当关键词不明确时，调用 LLM 判断
    3. 默认回退：无法判断时路由到 GENERAL 角色

    Args:
        profiles: 可用的 Agent 角色配置。
        llm: 用于路由决策的 LLM 实例（可选）。
    """

    def __init__(
        self,
        *,
        profiles: dict[AgentRole, AgentProfile] | None = None,
        llm: Any | None = None,
    ) -> None:
        self._profiles = profiles or DEFAULT_PROFILES
        self._llm = llm

    async def route(self, user_message: str) -> tuple[AgentRole, str]:
        """分析用户消息并返回推荐的角色。

        Args:
            user_message: 用户消息。

        Returns:
            (推荐角色, 路由理由)。
        """
        # 快速路径：关键词匹配
        role = self._keyword_match(user_message)
        if role is not None:
            reason = f"关键词匹配到 {role.value} 角色"
            logger.debug("路由决策（关键词）: role=%s", role.value)
            return role, reason

        # 精确路径：LLM 路由
        if self._llm is not None:
            role, reason = await self._llm_route(user_message)
            if role is not None:
                logger.debug("路由决策（LLM）: role=%s", role.value)
                return role, reason

        # 默认回退
        logger.debug("路由决策（默认）: role=general")
        return AgentRole.GENERAL, "无法确定角色，使用通用 Agent"

    def get_profile(self, role: AgentRole) -> AgentProfile:
        """获取指定角色的配置。

        Args:
            role: Agent 角色。

        Returns:
            角色配置。
        """
        return self._profiles.get(role, DEFAULT_PROFILES[AgentRole.GENERAL])

    @staticmethod
    def _keyword_match(message: str) -> AgentRole | None:
        """关键词匹配路由。"""
        msg_lower = message.lower()

        # 代码相关关键词
        code_keywords = [
            "写代码", "修改代码", "debug", "修复bug", "重构",
            "function", "class", "方法", "函数", "实现",
            "代码", "编程", "编程", "script", "程序",
        ]
        if any(kw in msg_lower for kw in code_keywords):
            return AgentRole.CODER

        # 研究相关关键词
        research_keywords = [
            "搜索", "查找资料", "research", "调查", "分析",
            "总结", "对比", "web_search", "搜索一下",
        ]
        if any(kw in msg_lower for kw in research_keywords):
            return AgentRole.RESEARCHER

        # 审查相关关键词
        review_keywords = [
            "审查", "review", "检查代码", "code review", "质量",
            "发现bug", "问题", "审查一下",
        ]
        if any(kw in msg_lower for kw in review_keywords):
            return AgentRole.REVIEWER

        return None

    async def _llm_route(self, user_message: str) -> tuple[AgentRole | None, str]:
        """LLM 路由决策。"""
        from langchain_core.messages import HumanMessage, SystemMessage

        role_descriptions = "\n".join(
            f"- {profile.role.value}: {profile.description} (能力: {', '.join(profile.capabilities)})"
            for profile in self._profiles.values()
            if profile.role != AgentRole.ROUTER
        )

        system_prompt = _ROUTER_PROMPT.format(role_descriptions=role_descriptions)

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message[:500]),
            ]
            response = await self._llm.ainvoke(messages)
            content = response.content if hasattr(response, "content") else str(response)

            # 解析 JSON
            json_match = re.search(r"\{[^}]+\}", content)
            if json_match:
                data = json.loads(json_match.group())
                role_str = data.get("role", "general")
                try:
                    return AgentRole(role_str), data.get("reason", "")
                except ValueError:
                    pass

        except Exception as e:
            logger.warning("LLM 路由失败: %s", str(e)[:200])

        return None, ""
