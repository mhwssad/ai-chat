"""多 Agent 团队编排 — 支持"编排者-执行者"和"辩论"两种协作模式。

职责：
1. 编排者-执行者模式：ROUTER 分发任务给专业 Agent，汇总结果
2. 辩论模式：多个 Agent 对同一问题给出独立方案，评判选择最优
3. 管理 Agent 生命周期和任务流转
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.ai.config.logging_setup import get_logger
from src.ai.core.agent.handoff import AgentHandoff
from src.ai.core.agent.roles import AgentProfile, AgentRole, DEFAULT_PROFILES
from src.ai.core.agent.router import AgentRouter

logger = get_logger(__name__)


class TeamMode(str, Enum):
    """团队协作模式。"""

    ORCHESTRATOR = "orchestrator"  # 编排者-执行者模式
    DEBATE = "debate"              # 辩论模式


@dataclass
class TeamResult:
    """团队协作结果。"""

    mode: TeamMode
    final_answer: str
    contributions: list[dict[str, Any]] = field(default_factory=list)
    handoffs: list[dict[str, str]] = field(default_factory=list)
    winner_role: AgentRole | None = None


class AgentTeam:
    """Agent 团队编排器。

    支持两种协作模式：
    1. 编排者-执行者：Router 分析意图 → 分发给专业 Agent → 汇总结果
    2. 辩论模式：多个 Agent 独立回答 → 评判选择最优

    Args:
        router: Agent 路由器。
        handoff: 交接管理器。
        profiles: Agent 角色配置。
        execute_fn: 异步执行函数 (role, system_prompt, user_message, tools) -> result。
    """

    def __init__(
        self,
        *,
        router: AgentRouter | None = None,
        handoff: AgentHandoff | None = None,
        profiles: dict[AgentRole, AgentProfile] | None = None,
        execute_fn: Any | None = None,
    ) -> None:
        self._router = router or AgentRouter()
        self._handoff = handoff or AgentHandoff()
        self._profiles = profiles or DEFAULT_PROFILES
        self._execute_fn = execute_fn

    async def run_orchestrator(
        self,
        user_message: str,
        *,
        max_handoffs: int = 3,
    ) -> TeamResult:
        """编排者-执行者模式。

        流程：
        1. Router 分析意图，选择最合适的 Agent
        2. 执行 Agent 任务
        3. 如需交接，创建 handoff 并继续
        4. 汇总最终结果

        Args:
            user_message: 用户消息。
            max_handoffs: 最大交接次数（防止无限循环）。

        Returns:
            团队协作结果。
        """
        contributions: list[dict[str, Any]] = []
        handoff_records: list[dict[str, str]] = []
        current_message = user_message
        current_role, reason = await self._router.route(user_message)

        logger.info(
            "编排者模式启动: initial_role=%s, reason=%s",
            current_role.value,
            reason[:100],
        )

        for i in range(max_handoffs + 1):
            profile = self._router.get_profile(current_role)

            # 执行 Agent 任务
            if self._execute_fn is not None:
                result = await self._execute_fn(
                    current_role,
                    profile.system_prompt,
                    current_message,
                    profile.allowed_tools,
                )
            else:
                result = f"[模拟] {current_role.value} 处理: {current_message[:100]}"

            contributions.append({
                "role": current_role.value,
                "agent_name": profile.name,
                "result": result if isinstance(result, str) else str(result),
                "iteration": i,
            })

            # 检查是否需要交接（简化：仅当结果是交接请求时）
            next_role = self._detect_handoff_request(result)
            if next_role is None or next_role == current_role or i >= max_handoffs:
                break

            # 执行交接
            handoff_ctx = self._handoff.create_handoff(
                from_role=current_role,
                to_role=next_role,
                task_description=current_message,
                partial_result=result if isinstance(result, str) else str(result),
            )

            handoff_records.append({
                "from": current_role.value,
                "to": next_role.value,
                "task": current_message[:100],
            })

            # 构建下一条消息（含交接上下文）
            current_message = handoff_ctx.to_system_message() + f"\n\n用户原始请求：{user_message}"
            current_role = next_role

        # 汇总最终答案
        final_answer = contributions[-1]["result"] if contributions else "无结果"

        return TeamResult(
            mode=TeamMode.ORCHESTRATOR,
            final_answer=final_answer,
            contributions=contributions,
            handoffs=handoff_records,
        )

    async def run_debate(
        self,
        user_message: str,
        *,
        participants: list[AgentRole] | None = None,
    ) -> TeamResult:
        """辩论模式。

        流程：
        1. 多个 Agent 独立回答同一问题
        2. 收集所有方案
        3. 由 Router 评判选择最优

        Args:
            user_message: 用户消息。
            participants: 参与辩论的角色列表。

        Returns:
            团队协作结果。
        """
        if participants is None:
            participants = [AgentRole.CODER, AgentRole.RESEARCHER, AgentRole.REVIEWER]

        contributions: list[dict[str, Any]] = []

        # 各 Agent 独立回答
        for role in participants:
            profile = self._router.get_profile(role)

            if self._execute_fn is not None:
                result = await self._execute_fn(
                    role,
                    profile.system_prompt,
                    user_message,
                    profile.allowed_tools,
                )
            else:
                result = f"[模拟] {role.value} 的回答"

            contributions.append({
                "role": role.value,
                "agent_name": profile.name,
                "result": result if isinstance(result, str) else str(result),
            })

        # 选择最优方案（使用第一个参与者的结果作为简化实现）
        winner = participants[0] if participants else AgentRole.GENERAL
        final_answer = contributions[0]["result"] if contributions else "无结果"

        logger.info(
            "辩论模式完成: participants=%s, winner=%s",
            [p.value for p in participants],
            winner.value,
        )

        return TeamResult(
            mode=TeamMode.DEBATE,
            final_answer=final_answer,
            contributions=contributions,
            winner_role=winner,
        )

    @staticmethod
    def _detect_handoff_request(result: Any) -> AgentRole | None:
        """检测 Agent 结果中是否包含交接请求。

        简化实现：检查结果文本中是否包含特定格式。
        """
        import re

        if not isinstance(result, str):
            return None

        # 检查 JSON 格式的交接请求
        match = re.search(r"\{\"handoff\":\s*\"(\w+)\"", result)
        if match:
            try:
                return AgentRole(match.group(1))
            except ValueError:
                pass

        return None
