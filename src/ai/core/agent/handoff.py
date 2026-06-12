"""Agent 任务交接协议 — Agent 之间的任务交接和上下文传递。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.ai.config.logging_setup import get_logger
from src.ai.core.agent.roles import AgentRole

logger = get_logger(__name__)


@dataclass
class HandoffContext:
    """任务交接上下文。

    从一个 Agent 传递给另一个 Agent 的信息包。

    Attributes:
        from_role: 源 Agent 角色。
        to_role: 目标 Agent 角色。
        task_description: 任务描述。
        partial_result: 中间结果（如果有）。
        notes: 附带的说明或约束。
        artifacts: 产出物（代码片段、文件路径等）。
    """

    from_role: AgentRole
    to_role: AgentRole
    task_description: str
    partial_result: str | None = None
    notes: list[str] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)

    def to_system_message(self) -> str:
        """生成交接上下文的系统消息。

        Returns:
            可注入到目标 Agent 系统提示词中的上下文文本。
        """
        parts: list[str] = [
            f"【任务交接】来自 {self.from_role.value} Agent",
            f"任务描述：{self.task_description}",
        ]

        if self.partial_result:
            parts.append(f"当前进展：{self.partial_result[:500]}")

        if self.notes:
            parts.append("注意事项：")
            for note in self.notes:
                parts.append(f"  - {note}")

        if self.artifacts:
            parts.append("产出物：")
            for key, value in self.artifacts.items():
                parts.append(f"  - {key}: {str(value)[:200]}")

        return "\n".join(parts)


class AgentHandoff:
    """Agent 任务交接管理器。

    管理多个 Agent 之间的任务流转：
    - 记录交接历史
    - 构建交接上下文
    - 验证交接合法性

    Args:
        allowed_handoffs: 允许的交接路径（源角色 → 目标角色列表）。
            如果为 None，则允许任意交接。
    """

    # 默认允许的交接路径
    DEFAULT_HANDOFFS: dict[AgentRole, list[AgentRole]] = {
        AgentRole.ROUTER: [
            AgentRole.CODER,
            AgentRole.RESEARCHER,
            AgentRole.REVIEWER,
            AgentRole.GENERAL,
        ],
        AgentRole.CODER: [AgentRole.REVIEWER, AgentRole.GENERAL],
        AgentRole.RESEARCHER: [AgentRole.CODER, AgentRole.GENERAL],
        AgentRole.REVIEWER: [AgentRole.CODER, AgentRole.GENERAL],
        AgentRole.GENERAL: [AgentRole.CODER, AgentRole.RESEARCHER, AgentRole.REVIEWER],
    }

    def __init__(
        self,
        *,
        allowed_handoffs: dict[AgentRole, list[AgentRole]] | None = None,
    ) -> None:
        self._allowed = allowed_handoffs or self.DEFAULT_HANDOFFS
        self._history: list[HandoffContext] = []

    def can_handoff(self, from_role: AgentRole, to_role: AgentRole) -> bool:
        """检查交接是否允许。

        Args:
            from_role: 源角色。
            to_role: 目标角色。

        Returns:
            True 表示允许交接。
        """
        allowed_targets = self._allowed.get(from_role, [])
        return to_role in allowed_targets

    def create_handoff(
        self,
        *,
        from_role: AgentRole,
        to_role: AgentRole,
        task_description: str,
        partial_result: str | None = None,
        notes: list[str] | None = None,
        artifacts: dict[str, Any] | None = None,
    ) -> HandoffContext:
        """创建任务交接上下文。

        Args:
            from_role: 源 Agent 角色。
            to_role: 目标 Agent 角色。
            task_description: 任务描述。
            partial_result: 中间结果。
            notes: 附带说明。
            artifacts: 产出物。

        Returns:
            交接上下文。

        Raises:
            ValueError: 交接路径不被允许。
        """
        if not self.can_handoff(from_role, to_role):
            raise ValueError(
                f"不允许的交接路径: {from_role.value} → {to_role.value}"
            )

        context = HandoffContext(
            from_role=from_role,
            to_role=to_role,
            task_description=task_description,
            partial_result=partial_result,
            notes=notes or [],
            artifacts=artifacts or {},
        )

        self._history.append(context)
        logger.info(
            "任务交接: %s → %s, task=%s",
            from_role.value,
            to_role.value,
            task_description[:100],
        )

        return context

    @property
    def history(self) -> list[HandoffContext]:
        """获取交接历史。"""
        return list(self._history)
