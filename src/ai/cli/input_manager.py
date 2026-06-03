"""平台输入抽象 — msvcrt/Unix 键盘输入统一接口。"""

from __future__ import annotations

import collections
import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Callable

logger = logging.getLogger(__name__)


class InputBackend(ABC):
    """输入后端抽象基类。"""

    @abstractmethod
    def read_key(self) -> str | None:
        """读取一个按键，无按键时返回 None。"""


class MsvcrtBackend(InputBackend):
    """Windows msvcrt 输入后端。"""

    def read_key(self) -> str | None:
        try:
            import msvcrt

            if not msvcrt.kbhit():
                return None

            ch = msvcrt.getwch()

            # 处理特殊键前缀
            if ch in ("\x00", "\xe0"):
                ch2 = msvcrt.getwch()
                return self._translate_special(ch2)
            elif ch == "\x1b":
                return self._read_escape_seq()
            elif ch in ("\r", "\n"):
                return "enter"
            elif ch == "\x03":
                return "ctrl_c"
            elif ch == "\x08":
                return "backspace"
            else:
                return f"char:{ch}"
        except Exception:
            return None

    @staticmethod
    def _translate_special(ch: str) -> str:
        """翻译 msvcrt 特殊键码。"""
        mapping = {
            "H": "up",
            "P": "down",
            "K": "left",
            "M": "right",
            "G": "home",
            "O": "end",
            "I": "page_up",
            "Q": "page_down",
            "S": "delete",
        }
        return mapping.get(ch, f"special:{ch}")

    @staticmethod
    def _read_escape_seq() -> str:
        """读取 Escape 序列（VT 模式箭头键等）。"""
        try:
            import msvcrt

            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch == "[":
                    if msvcrt.kbhit():
                        code = msvcrt.getwch()
                        vt_map = {
                            "A": "up",
                            "B": "down",
                            "C": "right",
                            "D": "left",
                            "H": "home",
                            "F": "end",
                            "1": "home",
                            "2": "insert",
                            "3": "delete",
                            "4": "end",
                            "5": "page_up",
                            "6": "page_down",
                        }
                        result = vt_map.get(code, f"vt:{code}")
                        if code in ("1", "2", "3", "4", "5", "6") and msvcrt.kbhit():
                            msvcrt.getwch()
                        return result
                return f"esc_seq:{ch}"
        except Exception:
            pass
        return "escape"


class UnixBackend(InputBackend):
    """Unix select + stdin 输入后端。"""

    def __init__(self) -> None:
        self._old_settings = None
        self._fd = None

    def setup(self) -> None:
        """设置终端为 cbreak 模式。"""
        import sys
        import termios
        import tty

        self._fd = sys.stdin.fileno()  # type: ignore[assignment]
        self._old_settings = termios.tcgetattr(self._fd)  # type: ignore[attr-defined]
        tty.setcbreak(self._fd)  # type: ignore[attr-defined]

    def restore(self) -> None:
        """恢复终端设置。"""
        if self._old_settings is not None and self._fd is not None:
            import termios

            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_settings)

    def read_key(self) -> str | None:
        import select
        import sys

        if not select.select([sys.stdin], [], [], 0.05)[0]:
            return None

        ch = sys.stdin.read(1)

        if ch == "\x1b":
            rest = ""
            if select.select([sys.stdin], [], [], 0.02)[0]:
                rest = sys.stdin.read(2)
            if rest == "[A":
                return "up"
            elif rest == "[B":
                return "down"
            elif rest == "[C":
                return "right"
            elif rest == "[D":
                return "left"
            elif rest == "[H":
                return "home"
            elif rest == "[F":
                return "end"
            elif rest and len(rest) == 2 and rest[0] == "[" and rest[1] in "123456":
                code = rest[1]
                if select.select([sys.stdin], [], [], 0.02)[0]:
                    sys.stdin.read(1)
                long_map = {
                    "1": "home",
                    "2": "insert",
                    "3": "delete",
                    "4": "end",
                    "5": "page_up",
                    "6": "page_down",
                }
                return long_map.get(code, f"vt:{code}")
            else:
                return "escape"
        elif ch in ("\r", "\n"):
            return "enter"
        elif ch == "\x03":
            return "ctrl_c"
        elif ch == "\x7f":
            return "backspace"
        else:
            return f"char:{ch}"


class InputManager:
    """输入管理器 — 统一的键盘输入接口。

    自动选择平台适配的输入后端（Windows msvcrt / Unix select）。

    Args:
        running_ref: 运行标志引用（callable 返回 bool）。
    """

    def __init__(self, running_ref: Callable[[], bool]) -> None:
        self._running_ref = running_ref
        self._queue: collections.deque[str] = collections.deque(maxlen=64)
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._backend: InputBackend = self._create_backend()

    @staticmethod
    def _create_backend() -> InputBackend:
        """创建平台适配的输入后端。"""
        try:
            import msvcrt  # noqa: F401

            return MsvcrtBackend()
        except ImportError:
            return UnixBackend()

    def start(self) -> None:
        """启动输入线程。"""
        if isinstance(self._backend, UnixBackend):
            self._backend.setup()

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止输入线程。"""
        if isinstance(self._backend, UnixBackend):
            self._backend.restore()

    def poll(self) -> str:
        """获取下一个按键（非阻塞）。

        Returns:
            按键标识符，队列为空返回空字符串。
        """
        with self._lock:
            return self._queue.popleft() if self._queue else ""

    def _loop(self) -> None:
        """输入线程主循环。"""
        while self._running_ref():
            try:
                key = self._backend.read_key()
                if key is not None:
                    with self._lock:
                        self._queue.append(key)
                else:
                    time.sleep(0.02)
            except Exception as e:
                logger.debug("输入线程异常: %s", e)
                time.sleep(0.1)
