"""工具子系统 DI 容器。"""

from dependency_injector import containers, providers


def _create_tool_registry():
    """工具注册表。"""
    from src.ai.core.tools.registry import ToolRegistry

    return ToolRegistry()


def _create_tool_manager(registry, http_aclient, mcp_manager):
    """构建 ToolManager 并加载内置工具。"""
    from src.ai.core.tools.manager import ToolManager

    mgr = ToolManager(
        registry=registry,
        http_aclient=http_aclient,
        mcp_manager=mcp_manager,
    )
    mgr.load_builtin_tools()
    return mgr


class ToolContainer(containers.DeclarativeContainer):
    """工具子系统容器。"""

    # 外部依赖
    http_aclient = providers.Dependency()
    mcp_manager = providers.Dependency()

    tool_registry = providers.Singleton(_create_tool_registry)
    tool_manager = providers.Singleton(
        _create_tool_manager,
        registry=tool_registry,
        http_aclient=http_aclient,
        mcp_manager=mcp_manager,
    )
