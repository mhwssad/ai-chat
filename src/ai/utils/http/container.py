"""HTTP 工具子系统 DI 容器。"""

from dependency_injector import containers, providers


def _create_http_client():
    """同步 HTTP 客户端（返回模块级单例）。"""
    from src.ai.utils.http.client import http_client

    return http_client


def _create_http_aclient():
    """异步 HTTP 客户端（返回模块级单例）。"""
    from src.ai.utils.http.client import http_aclient

    return http_aclient


def _create_converter_registry():
    """HTTP 响应转换器注册表（返回模块级单例）。"""
    from src.ai.utils.http.converter import converter_registry

    return converter_registry


class HTTPContainer(containers.DeclarativeContainer):
    """HTTP 工具子系统容器。"""

    http_client = providers.Singleton(_create_http_client)
    http_aclient = providers.Singleton(_create_http_aclient)
    converter_registry = providers.Singleton(_create_converter_registry)
