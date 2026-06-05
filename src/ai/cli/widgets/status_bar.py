"""顶部状态栏组件。"""

import time

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.utils.theme import Icons


class StatusBar:
    """顶部状态栏 — 显示系统状态摘要。

    Attributes:
        model_name: 当前模型名称。
        scheduler_running: 调度器是否运行中。
        memory_count: 记忆条数。
        session_name: 当前会话名称。
        tool_count: 已注册工具数。
        active_tab_name: 当前活跃 Tab 名称。
    """

    def __init__(
        self,
        model_name: str = "未配置",
        scheduler_running: bool = False,
        memory_count: int = 0,
        session_name: str = "",
        tool_count: int = 0,
        active_tab_name: str = "",
        active_tab_status: str = "",
    ) -> None:
        self.model_name = model_name
        self.scheduler_running = scheduler_running
        self.memory_count = memory_count
        self.session_name = session_name
        self.tool_count = tool_count
        self.active_tab_name = active_tab_name
        self.active_tab_status = active_tab_status
        self._start_time: float = time.monotonic()

    def render(self, console: Console, width: int) -> Panel:
        """渲染状态栏面板。

        Args:
            console: Rich Console 实例。
            width: 可用宽度。

        Returns:
            状态栏 Panel。
        """
        text = Text()
        text.append(" AI Chat 控制台 ", style="title")
        text.append("| ", style="muted")
        text.append(f"模型: {self.model_name}", style="info")
        text.append(" | ", style="muted")

        sched_icon = Icons.RUNNING if self.scheduler_running else Icons.INACTIVE
        sched_style = "active" if self.scheduler_running else "inactive"
        text.append(f"调度器: {sched_icon} ", style=sched_style)
        text.append("| ", style="muted")
        text.append(f"记忆: {self.memory_count}", style="info")
        text.append(" | ", style="muted")
        text.append(f"工具: {self.tool_count}", style="info")

        # 运行时长
        uptime_seconds = int(time.monotonic() - self._start_time)
        uptime = self._format_uptime(uptime_seconds)
        text.append(" | ", style="muted")
        text.append(f"运行: {uptime}", style="muted")

        if self.session_name:
            text.append(" | ", style="muted")
            text.append(f"会话: {self.session_name}", style="highlight")

        if self.active_tab_name:
            text.append(" | ", style="muted")
            text.append(f"Tab: {self.active_tab_name}", style="info")
            if self.active_tab_status:
                text.append(" / ", style="muted")
                text.append(self.active_tab_status, style="muted")

        return Panel(
            text,
            style="header",
            width=width,
        )

    @staticmethod
    def _format_uptime(seconds: int) -> str:
        """格式化运行时长。"""
        if seconds < 60:
            return f"{seconds}s"
        if seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m"
