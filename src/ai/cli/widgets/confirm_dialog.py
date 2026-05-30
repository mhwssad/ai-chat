"""确认对话框组件。"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.utils.theme import Icons


class ConfirmDialog:
    """确认对话框 — 二次确认危险操作。

    Attributes:
        message: 确认消息。
        visible: 是否可见。
        result: 确认结果（None=未选择，True=确认，False=取消）。
    """

    def __init__(self) -> None:
        self.message: str = ""
        self.visible: bool = False
        self.result: bool | None = None
        self._selected: int = 0  # 0=否，1=是

    def show(self, message: str) -> None:
        """显示确认对话框。

        Args:
            message: 确认提示消息。
        """
        self.message = message
        self.visible = True
        self.result = None
        self._selected = 0

    def hide(self) -> None:
        """隐藏对话框。"""
        self.visible = False
        self.result = None

    def handle_input(self, key: str) -> bool:
        """处理输入。

        Args:
            key: 按键标识。

        Returns:
            True 表示已处理。
        """
        if not self.visible:
            return False

        if key in ("left", "right", "tab"):
            self._selected = 1 - self._selected
        elif key == "enter":
            self.result = self._selected == 1
            self.visible = False
        elif key == "escape" or key == "n":
            self.result = False
            self.visible = False
        elif key == "y":
            self.result = True
            self.visible = False

        return True

    def render(self, console: Console) -> Panel | None:
        """渲染对话框。

        Args:
            console: Rich Console 实例。

        Returns:
            Panel 对象，不可见时返回 None。
        """
        if not self.visible:
            return None

        text = Text()
        text.append(f"{Icons.WARNING} ", style="warning")
        text.append(self.message, style="warning")
        text.append("\n\n")

        # 按钮
        if self._selected == 0:
            text.append(" [ 否 ] ", style="selected")
            text.append("  ")
            text.append(" [ 是 ] ", style="muted")
        else:
            text.append(" [ 否 ] ", style="muted")
            text.append("  ")
            text.append(" [ 是 ] ", style="selected")

        text.append("\n\n")
        text.append("← → 切换 │ Enter 确认 │ Esc 取消", style="muted")

        return Panel(
            text,
            title="[warning]确认操作[/]",
            border_style="warning",
            width=50,
        )
