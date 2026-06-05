"""Agent 服务 — Agent 任务执行编排。"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AgentService:
    """Agent 服务。

    职责：
    1. 接收用户请求
    2. 调用 AgentOrchestrator 执行
    3. 返回结构化结果
    """

    def __init__(self, *, orchestrator: Any) -> None:
        self._orchestrator = orchestrator

    async def run(
        self,
        *,
        session_id: str,
        user_message: str,
        system_prompt: str | None = None,
        max_iterations: int = 10,
        tools: list[str] | None = None,
        agent_timeout: float = 300,
    ) -> dict[str, Any]:
        """执行 Agent 任务。

        Args:
            session_id: 会话 ID。
            user_message: 用户消息。
            system_prompt: 系统提示。
            max_iterations: 最大迭代次数。
            tools: 可用工具列表。
            agent_timeout: Agent 整体超时秒数。

        Returns:
            Agent 执行结果。
        """
        result = await self._orchestrator.run(
            session_id=session_id,
            user_message=user_message,
            system_prompt=system_prompt,
            max_iterations=max_iterations,
            tools=tools,
            agent_timeout=agent_timeout,
        )

        return result.to_dict()

    def cancel(self) -> dict[str, Any]:
        """取消当前 Agent 任务。"""
        cancelled = bool(self._orchestrator.cancel())
        return {
            "cancelled": cancelled,
            "status": "cancel_requested" if cancelled else "idle",
            "message": "已发送取消请求" if cancelled else "当前没有运行中的 Agent",
        }
