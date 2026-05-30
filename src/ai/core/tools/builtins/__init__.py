"""内置工具包 — 导入各子模块触发自注册。

无依赖的工具通过模块级 register_tool() 自注册。
有依赖的工具通过 register() 工厂函数注册，需要外部传入依赖。

MCP 和 Skills 工具由各自模块自行注册，不在此处管理。
"""

# 无依赖的工具：导入即自注册
from . import (
    file_tools,
    interaction_tools,
    notebook_tools,
    plan_tools,
    placeholder_tools,
    shell_tools,
    todo_tools,
    worktree_tools,
)

# 有依赖的工具模块（延迟导入，通过 register() 注册）
from . import scheduler_tools, search_tools, web_tools

__all__ = [
    "file_tools",
    "interaction_tools",
    "notebook_tools",
    "plan_tools",
    "placeholder_tools",
    "scheduler_tools",
    "search_tools",
    "shell_tools",
    "todo_tools",
    "web_tools",
    "worktree_tools",
    "register_dependent_tools",
]


def register_dependent_tools(
    *,
    http_aclient,
    mcp_manager,
    registry,
    scheduler_service=None,
) -> None:
    """注册有依赖的内置工具。

    Args:
        http_aclient: 异步 HTTP 客户端。
        mcp_manager: MCP 管理器实例（供 web_tools 使用）。
        registry: 工具注册表实例。
        scheduler_service: 定时任务服务实例（可选）。
    """
    web_tools.register(http_aclient, mcp_manager)
    search_tools.register(registry)
    if scheduler_service:
        scheduler_tools.register(scheduler_service)
