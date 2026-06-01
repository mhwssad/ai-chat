"""ASCII Spinner 组件 — 加载动画。"""

import time

from rich.text import Text


class Spinner:
    """ASCII 旋转动画。

    使用 ASCII 帧序列 ["|", "/", "-", "\\"] 实现终端旋转动画。

    Attributes:
        message: 伴随显示的消息。
        frames: 动画帧序列。
        interval: 帧切换间隔（秒）。
    """

    def __init__(
        self,
        message: str = "加载中",
        frames: list[str] | None = None,
        interval: float = 0.15,
    ) -> None:
        self.message = message
        self.frames = frames or ["|", "/", "-", "\\"]
        self.interval = interval
        self._start_time: float = time.monotonic()

    def render(self) -> Text:
        """渲染当前帧。

        Returns:
            包含帧动画、消息和已用时间的 Rich Text。
        """
        elapsed = time.monotonic() - self._start_time
        frame_idx = int(elapsed / self.interval) % len(self.frames)
        frame = self.frames[frame_idx]

        text = Text()
        text.append(f" {frame} ", style="warning")
        text.append(self.message, style="warning")
        text.append(f" ({elapsed:.0f}s)", style="muted")
        return text

    def reset(self) -> None:
        """重置动画计时。"""
        self._start_time = time.monotonic()
