from __future__ import annotations

"""CLI 异常处理封装 — 统一捕获并友好展示错误。

用法:
    from src.ai_chat.utils.error_handler import cli_run

    @cli_run
    def main():
        ...

异常优先级:
1. KeyboardInterrupt  → Ctrl+C，打印提示后继续
2. EOFError           → 管道关闭 / Ctrl+D，退出
3. BaseExceptions     → 项目自定义异常，打印格式化消息
4. Exception          → 兜底，打印 + 记录完整堆栈
"""

import functools
import sys
from typing import Any, Callable

from src.ai_chat.config.base_exception import BaseExceptions
from src.ai_chat.config.logging_setup import get_logger

logger = get_logger(__name__)


def cli_run(func: Callable) -> Callable:
    """装饰器：包装 CLI 函数，统一捕获异常。"""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            print("\n操作已取消")
        except EOFError:
            print("\n再见！")
            sys.exit(0)
        except BaseExceptions as e:
            logger.error(str(e))
            print(f"\n错误: {e}")
        except Exception as e:
            logger.exception("未预期的错误")
            print(f"\n系统错误: {e}")

    return wrapper
