"""TUI 工作台壳层。"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections.abc import Callable, Sequence
from typing import Any

from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.command_router import CommandRouter
from src.ai.cli.input_history import InputHistory
from src.ai.cli.input_manager import InputManager
from src.ai.cli.sessions import SessionManager
from src.ai.cli.tabs import BaseTab
from src.ai.cli.tabs.chat_tab import ChatTab
from src.ai.cli.utils.theme import Icons, get_theme, next_theme
from src.ai.cli.widgets.confirm_dialog import ConfirmDialog
from src.ai.cli.widgets.status_bar import StatusBar
from src.ai.service.types import ChatOptions

logger = logging.getLogger(__name__)

_HEADER_SIZE = 3
_FOOTER_SIZE = 4
_NAV_WIDTH = 24
_MID_BREAKPOINT = 110
_WIDE_BREAKPOINT = 160


class Dashboard:
    """统一 TUI 工作台。"""

    def __init__(
        self,
        *,
        session_mgr: SessionManager,
        tabs: Sequence[BaseTab],
        command_router: CommandRouter,
        thread_pool: Any,
        chat_service: Any,
        system_service: Any,
    ) -> None:
        self._console = Console(theme=get_theme())
        self._session_mgr = session_mgr
        self._tabs = list(tabs)
        self._command_router = command_router
        self._thread_pool = thread_pool
        self._chat_service = chat_service
        self._system_service = system_service

        self._status_bar = StatusBar()
        self._running = False
        self._active_tab_index = 0
        self._dirty = True
        self._lock = threading.Lock()

        self._last_message = ""
        self._message_time = 0.0
        self._status_refresh_time = 0.0
        self._status_refresh_interval = 10.0

        self._input_manager = InputManager(lambda: self._running)
        self._input_history = InputHistory()
        self._confirm_dialog = ConfirmDialog()
        self._pending_confirm_action: Callable[[], None] | None = None
        self._pending_confirm_decision: Callable[[bool], None] | None = None

        self._input_mode = False
        self._input_buffer = ""
        self._input_prompt = ""
        self._input_callback: Callable[[str], None] | None = None

        self._inspector_visible = True
        self._current_theme = "dark"
        self._layout_mode = "wide"
        self._tab_hotkeys: dict[str, int] = {}

        self._configure_tabs()

    def _configure_tabs(self) -> None:
        for index, tab in enumerate(self._tabs):
            tab.bind_ui(
                set_status=self._set_message,
                request_input=self._enter_input_mode,
                request_confirm=self._request_confirm,
                request_confirm_decision=self._request_confirm_decision,
                request_refresh=self._mark_dirty,
            )
            tab.register_commands(self._command_router, index)

            if tab.hotkey:
                self._tab_hotkeys[tab.hotkey] = index

            if isinstance(tab, ChatTab):
                tab.set_message_sender(self._send_chat_message)

    def run(self) -> None:
        """启动 TUI 主循环。"""
        self._running = True

        try:
            self._session_mgr.discover_existing_sessions()
        except Exception as exc:
            logger.debug("加载历史会话失败: %s", exc)

        if self._tabs:
            self._tabs[self._active_tab_index].on_activate()

        self._refresh_status(force=True)
        self._input_manager.start()

        try:
            with Live(
                self._build_screen(),
                console=self._console,
                refresh_per_second=6,
                screen=False,
            ) as live:
                while self._running:
                    self._process_pending_input()
                    self._refresh_status()

                    if self._dirty:
                        live.update(self._build_screen())
                        self._dirty = False

                    time.sleep(0.08)
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            self._running = False
            self._input_manager.stop()
            self._console.print("\n[info]已退出工作台[/]")

    def _set_message(self, message: str) -> None:
        self._last_message = message
        self._message_time = time.monotonic()
        self._dirty = True

    def _mark_dirty(self) -> None:
        self._dirty = True

    def _request_confirm(self, message: str, action: Callable[[], None]) -> None:
        self._pending_confirm_action = action
        self._pending_confirm_decision = None
        self._confirm_dialog.show(message)
        self._dirty = True

    def _request_confirm_decision(
        self, message: str, callback: Callable[[bool], None]
    ) -> None:
        self._pending_confirm_action = None
        self._pending_confirm_decision = callback
        self._confirm_dialog.show(message)
        self._dirty = True

    def _enter_input_mode(
        self,
        prompt: str,
        callback: Callable[[str], None],
    ) -> None:
        self._input_mode = True
        self._input_buffer = ""
        self._input_prompt = prompt
        self._input_callback = callback
        self._dirty = True

    def _exit_input_mode(self) -> None:
        self._input_mode = False
        self._input_buffer = ""
        self._input_prompt = ""
        self._input_callback = None
        self._dirty = True

    def _process_pending_input(self) -> None:
        for _ in range(10):
            key = self._input_manager.poll()
            if not key:
                return

            if self._confirm_dialog.visible:
                self._handle_confirm_input(key)
                continue

            if key == "ctrl_c":
                if self._input_mode:
                    self._exit_input_mode()
                else:
                    self._running = False
                return

            if self._input_mode:
                self._handle_input_mode(key)
                continue

            if key in ("up", "down", "enter", "escape"):
                self._active_tab.handle_input(key)
                self._dirty = True
                continue

            if key == "page_up":
                for _ in range(5):
                    self._active_tab.handle_input("up")
                self._dirty = True
                continue

            if key == "page_down":
                for _ in range(5):
                    self._active_tab.handle_input("down")
                self._dirty = True
                continue

            if key.startswith("char:"):
                self._handle_char_input(key[5:])

    def _handle_confirm_input(self, key: str) -> None:
        self._confirm_dialog.handle_input(key)
        if not self._confirm_dialog.visible:
            result = bool(self._confirm_dialog.result)
            if self._pending_confirm_decision is not None:
                self._pending_confirm_decision(result)
            elif result and self._pending_confirm_action is not None:
                self._pending_confirm_action()
            self._pending_confirm_action = None
            self._pending_confirm_decision = None
        self._dirty = True

    def _handle_char_input(self, ch: str) -> None:
        if ch in self._tab_hotkeys:
            self._switch_tab(self._tab_hotkeys[ch])
            return

        if ch == "q":
            self._running = False
            return

        if ch == "T":
            self._current_theme = next_theme()
            self._console = Console(theme=get_theme())
            self._set_message(f"[info]主题已切换: {self._current_theme}[/]")
            return

        if ch == "I":
            self._inspector_visible = not self._inspector_visible
            state = "开启" if self._inspector_visible else "关闭"
            self._set_message(f"[info]检视区已{state}[/]")
            return

        if ch == "[":
            self._cycle_tabs(-1)
            return

        if ch == "]":
            self._cycle_tabs(1)
            return

        handled = self._command_router.dispatch(self._active_tab_index, ch)
        if not handled:
            handled = self._active_tab.handle_input(ch)
        if handled:
            self._dirty = True

    def _handle_input_mode(self, key: str) -> None:
        if key == "enter":
            text = self._input_buffer.strip()
            if text and self._input_callback is not None:
                self._input_history.add(text)
                self._input_callback(text)
            self._exit_input_mode()
            return

        if key == "escape":
            self._exit_input_mode()
            self._input_history.reset()
            self._set_message("[info]已取消输入[/]")
            return

        if key == "backspace":
            self._input_buffer = self._input_buffer[:-1]
            self._dirty = True
            return

        if key == "up":
            prev = self._input_history.prev()
            if prev is not None:
                self._input_buffer = prev
            self._dirty = True
            return

        if key == "down":
            nxt = self._input_history.next()
            self._input_buffer = nxt if nxt is not None else ""
            self._dirty = True
            return

        if key.startswith("char:"):
            ch = key[5:]
            if ch and ord(ch) >= 32:
                self._input_buffer += ch
                self._dirty = True

    def _switch_tab(self, index: int) -> None:
        if index < 0 or index >= len(self._tabs) or index == self._active_tab_index:
            return

        self._active_tab.on_deactivate()
        self._active_tab_index = index
        self._active_tab.on_activate()
        self._refresh_status(force=True)
        self._dirty = True

    def _cycle_tabs(self, step: int) -> None:
        if not self._tabs:
            return
        next_index = (self._active_tab_index + step) % len(self._tabs)
        self._switch_tab(next_index)

    @property
    def _active_tab(self) -> BaseTab:
        return self._tabs[self._active_tab_index]

    def _refresh_status(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if not force and (now - self._status_refresh_time) < self._status_refresh_interval:
            return

        try:
            active = self._session_mgr.active_session
            if active is not None:
                self._session_mgr.refresh_message_count(active.session_id)
        except Exception as exc:
            logger.debug("刷新会话状态失败: %s", exc)

        try:
            status = self._system_service.get_runtime_status()
            self._status_bar.model_name = status.get("model_key", "未配置")
            self._status_bar.scheduler_running = bool(
                status.get("scheduler_running", False)
            )
            self._status_bar.memory_count = int(status.get("memory_count", 0))
            self._status_bar.tool_count = int(status.get("tool_count", 0))
        except Exception as exc:
            logger.debug("刷新系统状态失败: %s", exc)

        active = self._session_mgr.active_session
        self._status_bar.session_name = active.name if active else ""
        if self._tabs:
            summary = self._active_tab.get_summary()
            self._status_bar.active_tab_name = summary.title
            self._status_bar.active_tab_status = summary.status
        else:
            self._status_bar.active_tab_name = ""
            self._status_bar.active_tab_status = ""
        self._status_refresh_time = now
        self._dirty = True

    def _send_chat_message(self, message: str) -> None:
        active = self._session_mgr.active_session
        if active is None:
            self._set_message("[warning]请先创建或切换会话[/]")
            return

        chat_tab = self._find_chat_tab()
        if chat_tab is None:
            self._set_message("[error][X] 对话面板未加载[/]")
            return

        session_id = active.session_id
        chat_tab.set_pending_user_message(message)
        self._set_message("[info]消息已发送，正在等待回复[/]")

        def _run() -> None:
            try:
                result = asyncio.run(
                    self._chat_service.chat(
                        message,
                        session_id,
                        options=ChatOptions(session_id=session_id),
                    )
                )
                if result.error:
                    chat_tab.set_last_ai_response("")
                    self._set_message(f"[error][X] 对话失败: {result.error}[/]")
                    return

                chat_tab.set_last_ai_response(
                    result.content,
                    context_sources=result.context_sources,
                )
                self._session_mgr.refresh_message_count(session_id)
                self._set_message("[success][OK] 回复已完成[/]")
            except Exception as exc:
                logger.exception("发送对话消息失败")
                chat_tab.set_last_ai_response("")
                self._set_message(f"[error][X] 对话失败: {exc}[/]")
            finally:
                self._refresh_status(force=True)
                self._dirty = True

        self._thread_pool.run_bg(_run)

    def _find_chat_tab(self) -> ChatTab | None:
        for tab in self._tabs:
            if isinstance(tab, ChatTab):
                return tab
        return None

    def _build_screen(self) -> Group | Layout:
        width = max(80, self._console.size.width)
        height = max(24, self._console.size.height)
        self._layout_mode = self._pick_layout_mode(width)

        root = Layout(name="root")
        root.split_column(
            Layout(name="header", size=_HEADER_SIZE),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=_FOOTER_SIZE),
        )
        root["header"].update(self._status_bar.render(self._console, width))
        root["body"].update(self._build_body_layout(width, height - _HEADER_SIZE - _FOOTER_SIZE))
        root["footer"].update(self._render_footer(width))

        dialog = self._confirm_dialog.render(self._console)
        if dialog is None:
            return root
        return Group(root, Align.center(dialog, vertical="middle"))

    def _build_body_layout(self, width: int, height: int) -> Layout:
        active_tab = self._active_tab
        detail_visible = self._inspector_visible and active_tab.layout.prefer_detail

        nav_panel = self._render_navigation_panel()

        if self._layout_mode == "wide":
            detail_width = max(active_tab.layout.min_detail_width, width // 4)
            main_width = max(
                active_tab.layout.min_main_width,
                width - _NAV_WIDTH - detail_width - 8,
            )
            header_panel = self._render_workspace_header(active_tab)
            main_panel = active_tab.render_content(self._console, main_width, height - 5)

            body = Layout(name="body")
            if detail_visible:
                detail_panel = active_tab.get_detail_panel(
                    self._console,
                    detail_width,
                    height - 5,
                )
                body.split_row(
                    Layout(name="nav", size=_NAV_WIDTH),
                    Layout(name="workspace", ratio=active_tab.layout.main_ratio),
                    Layout(name="detail", ratio=active_tab.layout.detail_ratio),
                )
                body["nav"].update(nav_panel)
                body["detail"].update(
                    detail_panel
                    if detail_panel is not None
                    else self._render_placeholder_panel("当前面板没有详情视图")
                )
            else:
                body.split_row(
                    Layout(name="nav", size=_NAV_WIDTH),
                    Layout(name="workspace", ratio=1),
                )
                body["nav"].update(nav_panel)
            body["workspace"].update(self._stack_workspace(header_panel, main_panel))
            return body

        if self._layout_mode == "mid":
            workspace_width = width - _NAV_WIDTH - 4
            header_panel = self._render_workspace_header(active_tab)
            main_panel = active_tab.render_content(
                self._console,
                workspace_width,
                max(10, height - 10),
            )
            detail_panel = (
                active_tab.get_detail_panel(
                    self._console,
                    workspace_width,
                    max(8, height // 3),
                )
                if detail_visible
                else None
            )

            body = Layout(name="body")
            body.split_row(
                Layout(name="nav", size=_NAV_WIDTH),
                Layout(name="workspace", ratio=1),
            )
            body["nav"].update(nav_panel)
            workspace = Layout(name="workspace_shell")
            workspace.split_column(
                Layout(name="summary", size=5),
                Layout(name="main", ratio=1),
            )
            workspace["summary"].update(header_panel)
            workspace["main"].update(main_panel)
            if detail_panel is not None:
                workspace.split_column(
                    Layout(name="summary", size=5),
                    Layout(name="main", ratio=2),
                    Layout(name="detail", size=max(10, height // 3)),
                )
                workspace["summary"].update(header_panel)
                workspace["main"].update(main_panel)
                workspace["detail"].update(detail_panel)
            body["workspace"].update(workspace)
            return body

        header_panel = self._render_workspace_header(active_tab)
        main_panel = active_tab.render_content(self._console, width - 4, max(10, height - 10))
        detail_panel = (
            active_tab.get_detail_panel(self._console, width - 4, max(8, height // 3))
            if detail_visible
            else None
        )

        body = Layout(name="body")
        if detail_panel is None:
            body.split_column(
                Layout(name="summary", size=5),
                Layout(name="main", ratio=1),
            )
            body["summary"].update(header_panel)
            body["main"].update(main_panel)
        else:
            body.split_column(
                Layout(name="summary", size=5),
                Layout(name="main", ratio=2),
                Layout(name="detail", size=max(10, height // 3)),
            )
            body["summary"].update(header_panel)
            body["main"].update(main_panel)
            body["detail"].update(detail_panel)
        return body

    def _stack_workspace(self, header_panel: Panel, main_panel: Panel) -> Layout:
        layout = Layout(name="workspace")
        layout.split_column(
            Layout(name="summary", size=5),
            Layout(name="main", ratio=1),
        )
        layout["summary"].update(header_panel)
        layout["main"].update(main_panel)
        return layout

    def _render_navigation_panel(self) -> Panel:
        text = Text()
        text.append("工作台导航\n", style="subtitle")
        text.append(f"布局: {self._layout_mode}\n", style="muted")
        text.append(f"主题: {self._current_theme}\n", style="muted")
        text.append("\n", style="")

        for index, tab in enumerate(self._tabs):
            active = index == self._active_tab_index
            prefix = Icons.POINTER if active else " "
            label = f" {prefix} [{tab.hotkey}] {tab.name}\n"
            text.append(label, style="active" if active else "muted")

        active = self._session_mgr.active_session
        if active is not None:
            text.append("\n当前会话\n", style="subtitle")
            text.append(f"  {active.name}\n", style="value")
            text.append(f"  消息: {active.message_count}\n", style="muted")

        return Panel(text, title="[title]导航[/]", border_style="border")

    def _render_workspace_header(self, tab: BaseTab) -> Panel:
        summary = tab.get_summary()
        text = Text()
        text.append(f"{summary.title}\n", style="subtitle")
        text.append(
            f"模式: {summary.mode} | 壳层: {self._layout_mode} | 检视区: {'开' if self._inspector_visible else '关'}\n",
            style="muted",
        )
        if summary.status:
            text.append(f"{summary.status}\n", style="value")
        for label, value in summary.metrics[:3]:
            text.append(f"{label}: {value}\n", style="value")
        for line in summary.details[:3]:
            text.append(f"{line}\n", style="value")
        return Panel(text, title="[title]工作区[/]", border_style="border")

    def _render_footer(self, width: int) -> Panel:
        text = Text()

        if self._input_mode:
            text.append(f"{self._input_prompt}", style="key")
            text.append(self._input_buffer or " ", style="value")
            text.append("\nEnter 提交 | Esc 取消 | Up/Down 历史", style="muted")
            return Panel(text, title="[title]输入[/]", border_style="border", width=width)

        nav_parts = [f"[{tab.hotkey}] {tab.name}" for tab in self._tabs]
        text.append("切换: ", style="muted")
        text.append(" ".join(nav_parts[:5]), style="value")
        if len(nav_parts) > 5:
            text.append("\n", style="")
            text.append("      " + " ".join(nav_parts[5:]), style="value")

        commands = " ".join(
            f"{cmd.upper()} {label}" for cmd, label in self._active_tab.get_footer_commands()
        )
        text.append("\n", style="")
        text.append("命令: ", style="muted")
        text.append(commands or "-", style="value")
        text.append(" | I 检视区 | T 主题 | [/] 切页 | Q 退出", style="muted")

        if self._last_message and (time.monotonic() - self._message_time) <= 12:
            text.append("\n", style="")
            text.append("状态: ", style="muted")
            text.append_text(Text.from_markup(self._last_message))

        return Panel(text, title="[title]操作栏[/]", border_style="border", width=width)

    def _render_placeholder_panel(self, message: str) -> Panel:
        text = Text()
        text.append(f"  {message}\n", style="muted")
        return Panel(text, title="[title]检视区[/]", border_style="border")

    @staticmethod
    def _pick_layout_mode(width: int) -> str:
        if width >= _WIDE_BREAKPOINT:
            return "wide"
        if width >= _MID_BREAKPOINT:
            return "mid"
        return "narrow"
