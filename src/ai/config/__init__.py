"""配置与异常基础模块。

提供全局配置、日志、异常体系和错误分类的统一入口。
使用 PEP 562 惰性导入，避免 logging_setup → src.ai.config 循环依赖。
"""

__all__ = [
    # base_config
    "BaseSettingsConfig",
    "project_root",
    "env_file_path",
    # base_exception
    "BaseExceptions",
    # error_types
    "ErrorCategory",
    "StructuredError",
    "register_classification",
    "classify_exception",
    # logging_setup
    "LogLevel",
    "LogFormat",
    "LogConfig",
    "ColoredFormatter",
    "setup_logging",
    "get_logger",
    # settings
    "LLMSettings",
    "MemorySettings",
    "Settings",
    "settings",
]

_SUBMODULES = {
    "BaseSettingsConfig": ".base_config",
    "project_root": ".base_config",
    "env_file_path": ".base_config",
    "BaseExceptions": "src.ai.exception.base_exception",
    "ErrorCategory": ".error_types",
    "StructuredError": ".error_types",
    "register_classification": ".error_types",
    "classify_exception": ".error_types",
    "LogLevel": ".logging_setup",
    "LogFormat": ".logging_setup",
    "LogConfig": ".logging_setup",
    "ColoredFormatter": ".logging_setup",
    "setup_logging": ".logging_setup",
    "get_logger": ".logging_setup",
    "LLMSettings": ".settings",
    "MemorySettings": ".settings",
    "Settings": ".settings",
    "settings": ".settings",
}


def __getattr__(name: str):
    if name in _SUBMODULES:
        import importlib

        target = _SUBMODULES[name]
        mod = importlib.import_module(target, __name__) if target.startswith(".") else importlib.import_module(target)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return list(__all__)
