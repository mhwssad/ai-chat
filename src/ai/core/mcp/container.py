"""MCP 子系统 DI 容器。"""

from dependency_injector import containers, providers


def _create_mcp_config_repo(session_factory):
    """MCP 配置仓库。"""
    from pathlib import Path

    from src.ai.config.base_config import project_root
    from src.ai.config.container import config
    from src.ai.core.mcp.config import MCPConfigRepository

    config_path = Path(config.settings.mcp.mcp_config_file)
    if not config_path.is_absolute():
        config_path = project_root / config_path
    return MCPConfigRepository(
        config_path=config_path,
        session_factory=session_factory,
    )


def _create_mcp_manager(config_repo):
    """MCP 服务器管理器。"""
    from src.ai.core.mcp.manager import MCPManager

    return MCPManager(config_repo=config_repo)


class MCPContainer(containers.DeclarativeContainer):
    """MCP 子系统容器。"""

    session_factory = providers.Dependency()

    config_repo = providers.Singleton(
        _create_mcp_config_repo,
        session_factory=session_factory,
    )
    mcp_manager = providers.Singleton(_create_mcp_manager, config_repo=config_repo)
