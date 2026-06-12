"""多 Agent 角色定义 — AgentRole 枚举和 AgentProfile 数据类。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AgentRole(str, Enum):
    """Agent 角色枚举。"""

    ROUTER = "router"        # 路由：分析意图，分发给合适的 Agent
    CODER = "coder"          # 代码：编写、修改、调试代码
    RESEARCHER = "researcher"  # 研究：搜索、分析、总结信息
    REVIEWER = "reviewer"    # 审查：检查代码质量、发现 bug
    GENERAL = "general"      # 通用：处理不匹配特定角色的事务


@dataclass
class AgentProfile:
    """Agent 角色配置。

    每个 Agent 有独立的 system prompt、可用工具集和权限。

    Attributes:
        role: Agent 角色。
        name: 显示名称。
        system_prompt: 系统提示词。
        allowed_tools: 允许使用的工具名称列表（空列表表示全部）。
        denied_tools: 禁止使用的工具名称列表。
        max_iterations: 最大迭代次数。
        description: 角色描述（用于路由决策）。
        capabilities: 能力标签（用于路由匹配）。
    """

    role: AgentRole
    name: str
    system_prompt: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)
    max_iterations: int = 10
    description: str = ""
    capabilities: list[str] = field(default_factory=list)


# ── 预置角色配置 ──────────────────────────────────────────

DEFAULT_PROFILES: dict[AgentRole, AgentProfile] = {
    AgentRole.ROUTER: AgentProfile(
        role=AgentRole.ROUTER,
        name="Router Agent",
        system_prompt=(
            "你是一个智能路由器。分析用户的请求，判断应该交给哪个专业 Agent 处理。\n"
            "你只需要返回目标角色名称和理由，不需要执行具体任务。\n"
            "可用角色：coder（代码）、researcher（研究）、reviewer（审查）、general（通用）。\n"
            "请以 JSON 格式回复：{\"role\": \"<角色名>\", \"reason\": \"<理由>\"}"
        ),
        max_iterations=1,
        description="分析用户意图，路由到最合适的 Agent",
        capabilities=["intent_analysis", "routing"],
    ),
    AgentRole.CODER: AgentProfile(
        role=AgentRole.CODER,
        name="Coder Agent",
        system_prompt=(
            "你是一个专业的编程助手。擅长编写、修改和调试代码。\n"
            "你应该：\n"
            "1. 理解代码上下文和需求\n"
            "2. 编写清晰、可维护的代码\n"
            "3. 添加必要的注释和类型标注\n"
            "4. 验证代码的正确性"
        ),
        allowed_tools=["read_file", "write_file", "shell_command", "list_directory"],
        description="编写、修改、调试代码",
        capabilities=["code_generation", "debugging", "refactoring"],
    ),
    AgentRole.RESEARCHER: AgentProfile(
        role=AgentRole.RESEARCHER,
        name="Researcher Agent",
        system_prompt=(
            "你是一个专业的研究助手。擅长搜索、分析和总结信息。\n"
            "你应该：\n"
            "1. 使用搜索工具查找相关信息\n"
            "2. 分析和对比不同来源\n"
            "3. 提供结构化的总结和建议\n"
            "4. 注明信息来源"
        ),
        allowed_tools=["web_search", "read_file"],
        description="搜索、分析、总结信息",
        capabilities=["search", "analysis", "summarization"],
    ),
    AgentRole.REVIEWER: AgentProfile(
        role=AgentRole.REVIEWER,
        name="Reviewer Agent",
        system_prompt=(
            "你是一个严格的代码审查员。擅长发现代码中的问题和改进机会。\n"
            "你应该：\n"
            "1. 检查代码质量和可维护性\n"
            "2. 发现潜在的 bug 和安全问题\n"
            "3. 提出具体的改进建议\n"
            "4. 验证代码是否符合规范"
        ),
        allowed_tools=["read_file", "shell_command"],
        description="审查代码质量，发现 bug",
        capabilities=["code_review", "bug_detection", "quality_assurance"],
    ),
    AgentRole.GENERAL: AgentProfile(
        role=AgentRole.GENERAL,
        name="General Agent",
        system_prompt="你是一个通用的 AI 助手，可以处理各种类型的任务。",
        description="处理不匹配特定角色的通用任务",
        capabilities=["general"],
    ),
}
