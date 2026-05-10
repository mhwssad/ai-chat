"""日志配置与初始化模块。

合并自 log_config.py 和 log_init.py，提供统一的日志配置、格式化和初始化能力。
使用标准库 RotatingFileHandler 替代 rotatelogs 第三方依赖。
"""

import logging
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from pydantic import Field

from src.config.base_config import BaseSettingsConfig


class LogLevel(str, Enum):
    """日志级别枚举。"""

    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'


class LogFormat(str, Enum):
    """日志格式枚举。"""

    SIMPLE = 'simple'       # 简化格式
    STANDARD = 'standard'   # 标准格式
    DETAILED = 'detailed'   # 详细格式


class LogConfig(BaseSettingsConfig):
    """日志配置类，继承自 BaseSettingsConfig，支持环境变量加载。"""

    # 日志级别
    log_level: LogLevel = Field(default=LogLevel.INFO)

    # 日志格式
    log_format: LogFormat = Field(default=LogFormat.STANDARD)

    # 日志文件路径，None 表示只输出到控制台
    log_file: Optional[Path] = Field(default=None)

    # 日志文件最大大小（字节），默认 10MB
    log_max_bytes: int = Field(default=10 * 1024 * 1024)

    # 日志备份文件数量
    log_backup_count: int = Field(default=5)

    # 是否启用彩色输出（控制台）
    log_color: bool = Field(default=True)

    # 是否启用结构化日志输出（JSON）
    log_json: bool = Field(default=False)

    # 日志模块前缀
    loggers: dict[str, str] = Field(default_factory=lambda: {'': 'INFO'})

    model_config = {
        'env_prefix': 'LOG_',
        'env_file': '.env',
    }

    def get_formatter(self) -> logging.Formatter:
        """获取日志格式化器。

        根据当前配置返回对应的格式化器实例。

        Returns:
            与配置匹配的日志格式化器
        """
        if self.log_json:
            # 结构化日志格式
            return logging.Formatter(
                '{"time":"%(asctime)s","level":"%(levelname)s",'
                '"logger":"%(name)s","message":"%(message)s"}',
                datefmt='%Y-%m-%d %H:%M:%S',
            )
        if self.log_format == LogFormat.SIMPLE:
            return logging.Formatter('%(message)s')
        if self.log_format == LogFormat.DETAILED:
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - '
                '%(filename)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
            )
        # 标准格式
        return logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )


# ANSI 颜色码
_LEVEL_COLORS = {
    logging.DEBUG: '\033[36m',      # 青色
    logging.INFO: '\033[32m',       # 绿色
    logging.WARNING: '\033[33m',    # 黄色
    logging.ERROR: '\033[31m',      # 红色
    logging.CRITICAL: '\033[35m',   # 紫色
}
_COLOR_RESET = '\033[0m'


class ColoredFormatter(logging.Formatter):
    """按日志级别着色的格式化器，用于控制台输出。"""

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录，根据级别添加 ANSI 颜色码。

        Args:
            record: 日志记录对象

        Returns:
            着色后的格式化日志字符串
        """
        message = super().format(record)
        color = _LEVEL_COLORS.get(record.levelno, '')
        if color:
            return f'{color}{message}{_COLOR_RESET}'
        return message


def setup_logging(config: Optional[LogConfig] = None) -> logging.Logger:
    """设置日志系统。

    初始化根日志记录器，添加控制台和可选的文件处理器。
    使用标准库 RotatingFileHandler 实现日志文件轮转。

    Args:
        config: 日志配置实例，不提供则使用默认配置

    Returns:
        配置完成的根日志记录器
    """
    if config is None:
        config = LogConfig()

    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(config.log_level.value)

    # 清除已有的处理器，避免重复输出
    root_logger.handlers.clear()

    # 文件输出 - 使用标准库 RotatingFileHandler
    if config.log_file:
        file_handler = RotatingFileHandler(
            filename=str(config.log_file),
            maxBytes=config.log_max_bytes,
            backupCount=config.log_backup_count,
            encoding='utf-8',
        )
        file_handler.setLevel(config.log_level.value)
        file_handler.setFormatter(config.get_formatter())
        root_logger.addHandler(file_handler)

    # 控制台输出 - 使用着色格式化器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.log_level.value)
    colored_fmt = ColoredFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    console_handler.setFormatter(colored_fmt)
    root_logger.addHandler(console_handler)

    return root_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取日志记录器。

    Args:
        name: 日志记录器名称，None 表示获取根日志记录器

    Returns:
        指定名称的日志记录器
    """
    return logging.getLogger(name)
