"""TUI 主仪表盘 — Rich Live 布局 + 键盘事件循环。"""

import sys
import time

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.sessions import SessionManager
from src.ai.cli.tabs import BaseTab
from src.ai.cli.tabs.chat_tab import ChatTab
from src.ai.cli.tabs.tools_tab import ToolsTab
from src.ai.cli.tabs.memory_tab import MemoryTab
from src.ai.cli.tabs.scheduler_tab import SchedulerTab
from src.ai.cli.widgets.status_bar import StatusBar
from src.ai.cli.widgets.input_box import InputBox
from src.ai.cli.widgets.confirm_dialog import ConfirmDialog
from src.ai.cli.utils.theme import THEME


class Dashboard:
    """TUI 主仪表盘。

    布局：
    +---------------------------------------------------------------+
    | 状态栏（header）                                                |
    +---------------------------------------------------------------+
    | 左侧面板（会话/工具列表）  | 中间面板（Tab 内容）  | 右侧详情     |
    +---------------------------------------------------------------+
    | 底部输入栏 + 快捷键提示（footer）                               |
    +---------------------------------------------------------------+

    快捷键：
    - Tab/Shift+Tab: 切换 Tab
    - Q: 退出
    - N: 新建会话
    - Enter: 确认/执行
    - D: 删除（需确认）
    - /: 激活搜索
    - Esc: 取消
    - 上下箭头: 列表移动

    Attributes:
        _console: Rich Console 实例。
        _session_mgr: 会话管理器。
        _tabs: Tab 面板列表。
        _active_tab_index: 当前活跃 Tab 索引。
        _status_bar: 顶部状态栏。
        _input_box: 底部输入框。
        _confirm: 确认对话框。
        _running: 主循环标志。
    """

    def __init__(self, session_mgr: SessionManager) -> None:
        self._console = Console(theme=THEME, file=sys.stderr)
        self._session_mgr = session_mgr
        self._tabs: list[BaseTab] = [
            ChatTab(session_mgr),
            ToolsTab(),
            MemoryTab(),
            SchedulerTab(),
        ]
        self._active_tab_index: int = 0
        self._status_bar = StatusBar()
        self._input_box = InputBox()
        self._confirm = ConfirmDialog()
        self._running: bool = False
        self._last_error: str = ""

    def run(self) -> None:
        """启动 TUI 主循环。"""
        self._running = True

        # 尝试初始化服务信息
        self._init_status()

        try:
            with Live(
                self._build_layout(),
                console=self._console,
                refresh_per_second=8,
                screen=True,
            ) as live:
                while self._running:
                    # 读取键盘输入
                    key = self._read_key()
                    if key:
                        self._handle_key(key)

                    # 更新显示
                    live.update(self._build_layout())
                    time.sleep(0.05)
        except KeyboardInterrupt:
            pass
        finally:
            self._console.print("[info]已退出控制台[/]")

    def _init_status(self) -> None:
        """初始化状态栏信息。"""
        try:
            from src.ai.core.container import container

            # 模型信息
            try:
                chat_cfg = container.chat_model_config()
                self._status_bar.model_name = (
                    f"{chat_cfg.model_key} ({chat_cfg.backend})"
                )
            except Exception:
                self._status_bar.model_name = "未配置"

            # 调度器状态
            try:
                scheduler_svc = container.scheduler_container.scheduler_service()
                self._status_bar.scheduler_running = scheduler_svc.is_running
            except Exception:
                self._status_bar.scheduler_running = False

            # 记忆计数
            try:
                memory_svc = container.memory_container.memory_service()
                stats = memory_svc.get_stats()
                self._status_bar.memory_count = stats.get("total", 0)
            except Exception:
                self._status_bar.memory_count = 0

            # 发现已有会话
            self._session_mgr.discover_existing_sessions()
            if self._session_mgr.active_session:
                self._status_bar.session_name = self._session_mgr.active_session.name
        except Exception:
            pass

    def _build_layout(self) -> Layout:
        """构建 TUI 布局。"""
        layout = Layout()

        # 分割为 header / body / footer
        layout.split_column(
            Layout(name="header", size=1),
            Layout(name="body"),
            Layout(name="footer", size=1),
        )

        # Header: 状态栏
        width = self._console.width or 100
        layout["header"].update(self._status_bar.render(self._console, width))

        # Body: 三列布局
        layout["body"].split_row(
            Layout(name="sidebar", ratio=1, minimum_size=25),
            Layout(name="main", ratio=3),
            Layout(name="detail", ratio=2, minimum_size=25),
        )

        # 左侧：会话列表（始终显示）
        layout["sidebar"].update(self._render_sidebar())

        # 中间：当前活跃 Tab 内容
        active_tab = self._tabs[self._active_tab_index]
        layout["main"].update(
            active_tab.render_content(
                self._console, width // 2, self._console.height - 4
            )
        )

        # 右侧：详情面板
        detail = active_tab.get_detail_panel(
            self._console, width // 4, self._console.height - 4
        )
        if detail:
            layout["detail"].update(detail)
        else:
            layout["detail"].update(
                Panel(Text("  无详情", style="muted"), border_style="border")
            )

        # Footer: 输入栏 + Tab 切换
        layout["footer"].update(self._render_footer(width))

        return layout

    def _render_sidebar(self) -> Panel:
        """渲染左侧会话列表。"""
        text = Text()

        # Tab 切换区
        for i, tab in enumerate(self._tabs):
            prefix = "▸" if i == self._active_tab_index else " "
            style = "active" if i == self._active_tab_index else "muted"
            text.append(f" {prefix} [{tab.hotkey}] {tab.name}\n", style=style)

        text.append("\n", style="")
        text.append("─" * 24 + "\n", style="muted")
        text.append("会话列表\n", style="subtitle")

        sessions = self._session_mgr.list_sessions()
        if not sessions:
            text.append("  暂无会话\n", style="muted")
        else:
            for s in sessions:
                icon = "●" if s.is_active else "○"
                style = "active" if s.is_active else ""
                text.append(f" {icon} {s.name}", style=style)
                text.append(f" ({s.message_count})\n", style="muted")

        return Panel(text, title="[title]导航[/]", border_style="border")

    def _render_footer(self, width: int) -> Panel:
        """渲染底部栏。"""
        # 更新会话名称
        active = self._session_mgr.active_session
        if active:
            self._status_bar.session_name = active.name

        # Tab 切换提示
        text = Text()
        for i, tab in enumerate(self._tabs):
            prefix = "▸" if i == self._active_tab_index else " "
            text.append(
                f"{prefix}{tab.name} ",
                style="active" if i == self._active_tab_index else "muted",
            )
        text.append(" │ ", style="muted")

        # 快捷键提示
        text.append("Tab切换 Q退出 N新建 /搜索", style="muted")

        # 输入区
        if self._input_box.active:
            text.append(" │ ", style="muted")
            text.append(
                f"{self._input_box.prompt}{self._input_box.current_text}█",
                style="active",
            )
        elif self._last_error:
            text.append(" │ ", style="muted")
            text.append(self._last_error, style="error")

        return Panel(text, style="header", height=1, width=width)

    def _read_key(self) -> str | None:
        """读取键盘输入（跨平台）。

        Returns:
            按键标识字符串，或 None（无输入）。
        """
        if sys.platform == "win32":
            return self._read_key_windows()
        else:
            return self._read_key_unix()

    def _read_key_windows(self) -> str | None:
        """Windows 平台读取键盘（msvcrt）。"""
        import msvcrt

        if not msvcrt.kbhit():
            return None

        ch = msvcrt.getwch()

        # 功能键前缀
        if ch in ("\x00", "\xe0"):
            ch2 = msvcrt.getwch()
            key_map = {
                "H": "up",
                "P": "down",
                "K": "left",
                "M": "right",
                "S": "delete",
            }
            return key_map.get(ch2)

        # 普通键
        char_map = {
            "\t": "tab",
            "\r": "enter",
            "\n": "enter",
            "\x1b": "escape",
            "\x7f": "backspace",
            "\x08": "backspace",
            "\x03": "ctrl_c",
        }
        if ch in char_map:
            return char_map[ch]

        return ch

    def _read_key_unix(self) -> str | None:
        """Unix 平台读取键盘（termios + select）。"""
        import select
        import termios
        import tty

        # 非阻塞检查
        if not select.select([sys.stdin], [], [], 0)[0]:
            return None

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)

            if ch == "\x1b":
                # ESC 序列
                if select.select([sys.stdin], [], [], 0.01)[0]:
                    ch2 = sys.stdin.read(1)
                    if ch2 == "[":
                        ch3 = sys.stdin.read(1)
                        arrow_map = {"A": "up", "B": "down", "C": "right", "D": "left"}
                        return arrow_map.get(ch3)
                return "escape"

            char_map = {
                "\t": "tab",
                "\r": "enter",
                "\n": "enter",
                "\x7f": "backspace",
                "\x08": "backspace",
                "\x03": "ctrl_c",
            }
            return char_map.get(ch, ch)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _handle_key(self, key: str) -> None:
        """分发键盘事件。"""
        self._last_error = ""

        # 确认对话框优先
        if self._confirm.visible:
            self._confirm.handle_input(key)
            if self._confirm.result is not None:
                self._on_confirm_result(self._confirm.result)
            return

        # 输入框激活时
        if self._input_box.active:
            result = self._input_box.handle_char(key)
            if result is not None:
                self._on_input_submit(result)
            return

        # 全局快捷键
        if key == "q" or key == "ctrl_c":
            self._running = False
            return

        if key == "tab":
            self._active_tab_index = (self._active_tab_index + 1) % len(self._tabs)
            self._tabs[self._active_tab_index].on_activate()
            return

        if key == "shift_tab":
            self._active_tab_index = (self._active_tab_index - 1) % len(self._tabs)
            self._tabs[self._active_tab_index].on_activate()
            return

        if key == "n":
            self._input_box.activate(search=False)
            self._input_box.prompt = "新会话 ID: "
            return

        if key == "/":
            # 激活搜索（仅记忆 Tab 有效）
            if self._active_tab_index == 2:  # MemoryTab
                self._input_box.activate(search=True)
            return

        if key == "d":
            self._confirm.show("确认删除选中项?")
            return

        # Tab 面板处理
        self._tabs[self._active_tab_index].handle_input(key)

    def _on_input_submit(self, text: str) -> None:
        """处理输入框提交。"""
        tab = self._tabs[self._active_tab_index]

        # 搜索模式 → 记忆 Tab
        if self._input_box.search_mode and self._active_tab_index == 2:
            memory_tab: MemoryTab = tab  # type: ignore[assignment]
            memory_tab.set_search_query(text)
            return

        # 新建会话
        if self._input_box.prompt.startswith("新会话"):
            try:
                self._session_mgr.create_session(session_id=text)
                self._status_bar.session_name = text
            except ValueError as e:
                self._last_error = str(e)
            return

    def _on_confirm_result(self, confirmed: bool) -> None:
        """处理确认对话框结果。"""
        if not confirmed:
            return

        tab = self._tabs[self._active_tab_index]
        # 触发删除操作（通过模拟按 D 键的效果）
        if hasattr(tab, "_delete_selected"):
            tab._delete_selected()  # type: ignore[attr-defined]
