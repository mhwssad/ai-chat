"""工具子系统 DI 容器。"""

from dependency_injector import containers, providers


def _create_tool_registry():
    """工具注册表。"""
    from src.ai.core.tools.registry import ToolRegistry

    return ToolRegistry()


def _create_permission_checker(registry):
    """权限校验器。"""
    from src.ai.core.tools.permissions import PermissionChecker

    return PermissionChecker(registry=registry)


def _create_tool_manager(
    registry, http_aclient, model_service=None, permission_checker=None
):
    """构建 ToolManager。不加载内置工具，由 container_wiring 统一调度。"""
    from src.ai.core.tools.manager import ToolManager

    mgr = ToolManager(
        registry=registry,
        http_aclient=http_aclient,
        model_service=model_service,
        permission_checker=permission_checker,
    )
    return mgr


class ToolContainer(containers.DeclarativeContainer):
    """工具子系统容器。"""

    # 外部依赖
    http_aclient = providers.Dependency()
    model_service = providers.Dependency()

    tool_registry = providers.Singleton(_create_tool_registry)
    permission_checker = providers.Singleton(
        _create_permission_checker,
        registry=tool_registry,
    )
    tool_manager = providers.Singleton(
        _create_tool_manager,
        registry=tool_registry,
        http_aclient=http_aclient,
        model_service=model_service,
        permission_checker=permission_checker,
    )
