"""Tab 面板抽象基类。"""

from abc import ABC, abstractmethod

from rich.console import Console
from rich.panel import Panel


class BaseTab(ABC):
    """TUI 面板抽象基类。

    所有 Tab 面板（对话、工具、记忆、任务）继承此类，
    实现统一的渲染和事件处理接口。

    Attributes:
        name: Tab 显示名称。
        hotkey: 快捷键标识。
    """

    name: str = "未命名"
    hotkey: str = ""

    def __init__(self) -> None:
        self._selected_index: int = 0

    @abstractmethod
    def render_content(self, console: Console, width: int, height: int) -> Panel:
        """渲染面板主体内容。

        Args:
            console: Rich Console 实例。
            width: 可用宽度。
            height: 可用高度。

        Returns:
            Rich Panel 对象。
        """
        ...

    @abstractmethod
    def handle_input(self, key: str) -> bool:
        """处理键盘输入。

        Args:
            key: 按键标识（如 "up"、"down"、"enter"、"d" 等）。

        Returns:
            True 表示已处理，False 表示未处理（向上冒泡）。
        """
        ...

    def get_detail_panel(
        self, console: Console, width: int, height: int
    ) -> Panel | None:
        """渲染右侧详情面板（可选）。

        Args:
            console: Rich Console 实例。
            width: 可用宽度。
            height: 可用高度。

        Returns:
            Rich Panel 对象，或 None 表示不显示详情。
        """
        return None

    def on_activate(self) -> None:
        """Tab 被激活时的回调。"""
        pass

    def on_deactivate(self) -> None:
        """Tab 被取消激活时的回调。"""
        pass

    def _move_selection(self, delta: int, item_count: int) -> None:
        """移动选中索引。

        Args:
            delta: 移动方向（+1 向下，-1 向上）。
            item_count: 总项目数。
        """
        if item_count == 0:
            self._selected_index = 0
            return
        self._selected_index = max(0, min(self._selected_index + delta, item_count - 1))

    def _clamp_selection(self, item_count: int) -> None:
        """修正选中索引到合法范围。"""
        if item_count == 0:
            self._selected_index = 0
        else:
            self._selected_index = min(self._selected_index, item_count - 1)


__all__ = ["BaseTab"]
