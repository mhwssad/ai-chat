"""输入框组件 — 处理命令行输入和搜索。"""

from rich.console import Console
from rich.text import Text

from src.ai.cli.utils.theme import Icons


class InputBox:
    """底部输入框 — 单行文本输入。

    Attributes:
        prompt: 输入提示符。
        buffer: 当前输入缓冲区。
        active: 是否处于激活状态（可输入）。
        search_mode: 是否处于搜索模式。
    """

    def __init__(self, prompt: str = "> ") -> None:
        self.prompt = prompt
        self.buffer: str = ""
        self.active: bool = False
        self.search_mode: bool = False

    def activate(self, search: bool = False) -> None:
        """激活输入框。

        Args:
            search: 是否以搜索模式激活。
        """
        self.active = True
        self.search_mode = search
        self.buffer = ""
        if search:
            self.prompt = f"{Icons.SEARCH} 搜索: "
        else:
            self.prompt = "> "

    def deactivate(self) -> None:
        """取消激活。"""
        self.active = False
        self.search_mode = False
        self.buffer = ""

    def handle_char(self, char: str) -> str | None:
        """处理单个字符输入。

        Args:
            char: 输入字符。

        Returns:
            如果按下 Enter 且有内容，返回输入文本；否则返回 None。
        """
        if not self.active:
            return None

        if char == "\r" or char == "\n":
            # Enter — 提交
            text = self.buffer.strip()
            self.deactivate()
            return text if text else None
        elif char == "\x1b":
            # Esc — 取消
            self.deactivate()
            return None
        elif char == "\x7f" or char == "\b":
            # Backspace
            self.buffer = self.buffer[:-1]
        elif len(char) == 1 and ord(char) >= 32:
            # 可见字符
            self.buffer += char

        return None

    def render(self, console: Console, width: int) -> Text:
        """渲染输入框。

        Args:
            console: Rich Console 实例。
            width: 可用宽度。

        Returns:
            Rich Text 对象。
        """
        text = Text()

        # 快捷键提示
        keys_hint = "Tab切换 │ Q退出 │ N新建 │ /搜索"
        text.append(keys_hint, style="muted")

        # 命令输入区
        remaining = width - len(keys_hint) - 10
        if remaining > 20:
            text.append(
                " " + "─" * (remaining - len(self.prompt) - 2) + " ", style="muted"
            )

        if self.active:
            text.append(f" {self.prompt}{self.buffer}█", style="active")
        else:
            text.append(f" {self.prompt}", style="muted")
            text.append("按 Enter 输入命令", style="muted")

        return text

    @property
    def current_text(self) -> str:
        """当前缓冲区文本。"""
        return self.buffer
