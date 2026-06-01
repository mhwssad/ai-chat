"""命令注册/分发 — 替代 if-elif 命令分发逻辑。"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class CommandRouter:
    """命令路由器。

    支持按 Tab 注册命令处理器，运行时按 (tab_index, cmd) 分发。

    Usage:
        router = CommandRouter()
        router.register(0, "n", lambda: print("new session"))
        router.register(0, "d", lambda: print("delete"))
        router.dispatch(0, "n")  # 执行 new session
    """

    def __init__(self) -> None:
        self._handlers: dict[tuple[int, str], Callable[..., Any]] = {}

    def register(self, tab_index: int, cmd: str, handler: Callable[..., Any]) -> None:
        """注册命令处理器。

        Args:
            tab_index: Tab 索引（0=Chat, 1=Tools, 2=Memory, 3=Scheduler）。
            cmd: 命令字符。
            handler: 处理函数。
        """
        self._handlers[(tab_index, cmd)] = handler

    def dispatch(self, tab_index: int, cmd: str) -> bool:
        """分发命令到对应处理器。

        Args:
            tab_index: Tab 索引。
            cmd: 命令字符。

        Returns:
            True 表示命令已处理，False 表示未找到处理器。
        """
        handler = self._handlers.get((tab_index, cmd))
        if handler is not None:
            handler()
            return True
        return False

    def has_command(self, tab_index: int, cmd: str) -> bool:
        """检查命令是否已注册。"""
        return (tab_index, cmd) in self._handlers

    def list_commands(self, tab_index: int) -> list[tuple[str, str]]:
        """列出指定 Tab 的所有命令。"""
        return [
            (cmd, handler.__doc__ or "")
            for (ti, cmd), handler in self._handlers.items()
            if ti == tab_index
        ]
