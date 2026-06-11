"""Agent API 服务 — 包装 AgentOrchestrator 和 AgentTeam。

共享服务层，CLI 和 API 路由统一使用。
"""

from __future__ import annotations

from dataclasses import asdict
from src.ai.config.logging_setup import get_logger
from typing import Any

logger = get_logger(__name__)


class AgentApiService:
    """Agent API 服务。

    职责：
    1. 运行 Agent 编排循环
    2. 取消正在执行的任务
    3. 从 checkpoint 恢复
    4. 多 Agent 团队模式（编排者/辩论）
    """

    def __init__(
        self,
        *,
        agent_orchestrator: Any,
        thread_pool: Any = None,
    ) -> None:
        self._orchestrator = agent_orchestrator
        self._thread_pool = thread_pool

    async def run(
        self,
        session_id: str,
        user_message: str,
        *,
        system_prompt: str | None = None,
        max_iterations: int = 10,
        tools: list[str] | None = None,
        agent_timeout: float = 300,
    ) -> dict[str, Any]:
        """运行 Agent 编排循环。

        Args:
            session_id: 会话 ID。
            user_message: 用户输入。
            system_prompt: 自定义系统提示词。
            max_iterations: 最大迭代轮数。
            tools: 工具白名单。
            agent_timeout: Agent 超时秒数。

        Returns:
            AgentResult 字典。
        """
        result = await self._run_in_pool(
            self._orchestrator.run,
            session_id=session_id,
            user_message=user_message,
            system_prompt=system_prompt,
            max_iterations=max_iterations,
            tools=tools,
            agent_timeout=agent_timeout,
        )
        return self._result_to_dict(result)

    def cancel(self) -> bool:
        """取消正在执行的 Agent 任务。

        Returns:
            是否成功取消。
        """
        return self._orchestrator.cancel()

    async def resume(
        self,
        session_id: str,
        user_message: str,
        *,
        max_iterations: int = 10,
        tools: list[str] | None = None,
        agent_timeout: float = 300,
    ) -> dict[str, Any]:
        """从 checkpoint 恢复 Agent 执行。

        Args:
            session_id: 会话 ID。
            user_message: 用户输入。
            max_iterations: 最大迭代轮数。
            tools: 工具白名单。
            agent_timeout: Agent 超时秒数。

        Returns:
            AgentResult 字典。
        """
        result = await self._run_in_pool(
            self._orchestrator.resume,
            session_id=session_id,
            user_message=user_message,
            max_iterations=max_iterations,
            tools=tools,
            agent_timeout=agent_timeout,
        )
        return self._result_to_dict(result)

    async def run_team_orchestrator(
        self,
        user_message: str,
        *,
        session_id: str | None = None,
        max_handoffs: int = 3,
    ) -> dict[str, Any]:
        """运行编排者团队模式。

        Args:
            user_message: 用户输入。
            session_id: 会话 ID（可选）。
            max_handoffs: 最大交接次数。

        Returns:
            TeamResult 字典。
        """
        team = self._build_team()
        result = await self._run_in_pool(
            team.run_orchestrator,
            user_message,
            max_handoffs=max_handoffs,
        )
        return asdict(result)

    async def run_team_debate(
        self,
        user_message: str,
        *,
        session_id: str | None = None,
        participants: list[str] | None = None,
    ) -> dict[str, Any]:
        """运行辩论团队模式。

        Args:
            user_message: 用户输入。
            session_id: 会话 ID（可选）。
            participants: 参与者角色列表。

        Returns:
            TeamResult 字典。
        """
        team = self._build_team()
        result = await self._run_in_pool(
            team.run_debate,
            user_message,
            participants=participants,
        )
        return asdict(result)

    # ── 内部工具 ──────────────────────────────────────────────

    def _build_team(self) -> Any:
        """构建 AgentTeam 实例。"""
        from src.ai.core.agent.team import AgentTeam

        return AgentTeam(execute_fn=self._orchestrator.run)

    @staticmethod
    def _result_to_dict(result: Any) -> dict[str, Any]:
        """将 AgentResult 转换为字典。"""
        return result.to_dict()

    async def _run_in_pool(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        """在线程池中运行同步函数。"""
        if self._thread_pool is not None:
            return await self._thread_pool.run_io(lambda: fn(*args, **kwargs))
        return fn(*args, **kwargs)
