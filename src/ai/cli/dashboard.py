"""TUI 控制台 — Rich Layout + Live 渲染。

采用 Rich Live 实时刷新 + Layout 分栏布局。
使用 InputManager 统一处理平台键盘输入。
"""

import logging
import threading
import time
from collections.abc import Callable

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from src.ai.cli.chat_executor import ChatExecutor
from src.ai.cli.command_router import CommandRouter
from src.ai.cli.input_history import InputHistory
from src.ai.cli.input_manager import InputManager
from src.ai.cli.sessions import SessionManager
from src.ai.cli.tabs import BaseTab
from src.ai.cli.tabs.chat_tab import ChatTab
from src.ai.cli.tabs.image_tab import ImageTab
from src.ai.cli.tabs.memory_tab import MemoryTab
from src.ai.cli.tabs.scheduler_tab import SchedulerTab
from src.ai.cli.tabs.stats_tab import StatsTab
from src.ai.cli.tabs.tools_tab import ToolsTab
from src.ai.cli.tabs.tts_tab import TTSTab
from src.ai.cli.utils.theme import THEME, next_theme, get_theme
from src.ai.cli.widgets.confirm_dialog import ConfirmDialog
from src.ai.cli.widgets.status_bar import StatusBar

logger = logging.getLogger(__name__)

# ── 布局尺寸常量 ─────────────────────────────────────────────

HEADER_HEIGHT = 3
TAB_BAR_HEIGHT = 1
FOOTER_HEIGHT = 3
SIDEBAR_RATIO = 1
MAIN_RATIO = 2
DETAIL_RATIO = 1

# ── Tab 名称到索引 ──────────────────────────────────────────

_TAB_NAMES = ["chat", "tools", "memory", "scheduler", "stats", "image", "tts"]
_TAB_LABELS = [
    ("1", "Chat", "对话管理"),
    ("2", "Tools", "工具管理"),
    ("3", "Memory", "记忆管理"),
    ("4", "Scheduler", "任务管理"),
    ("5", "Stats", "系统统计"),
    ("6", "Image", "图像管理"),
    ("7", "TTS", "语音管理"),
]


class Dashboard:
    """TUI 控制台 — Rich Layout + Live 渲染。

    架构：
    - 输入线程：msvcrt 逐字符读取，支持方向键/翻页/Enter/Escape
    - 渲染主线程：Rich Live 自动刷新，Layout 分栏布局
    - 状态共享：线程锁保护的共享状态

    Attributes:
        _console: Rich Console 实例。
        _session_mgr: 会话管理器。
        _tabs: Tab 面板列表。
        _active_tab_index: 当前活跃 Tab 索引。
        _status_bar: 顶部状态栏。
        _running: 主循环标志。
        _last_message: 底部反馈消息。
        _scroll_offset: 当前 Tab 的滚动偏移。
        _input_key: 输入线程缓冲的按键。
        _lock: 线程锁。
    """

    def __init__(self, session_mgr: SessionManager) -> None:
        self._console = Console(theme=THEME)
        self._session_mgr = session_mgr
        self._tabs: list[BaseTab] = [
            ChatTab(session_mgr),
            ToolsTab(),
            MemoryTab(),
            SchedulerTab(),
            StatsTab(),
            ImageTab(),
            TTSTab(),
        ]
        self._active_tab_index: int = 0
        self._status_bar = StatusBar()
        self._running: bool = False
        self._last_message: str = ""
        self._message_time: float = 0.0
        self._scroll_offset: int = 0
        self._lock = threading.Lock()

        # 输入管理器
        self._input_manager = InputManager(lambda: self._running)

        # 文本输入模式（用于 n 新建会话、/ 搜索、聊天等）
        self._input_mode: bool = False
        self._input_buffer: str = ""
        self._input_prompt: str = ""
        self._input_callback: Callable[[str], None] | None = None

        # 对话状态
        self._chat_thinking: bool = False
        self._chat_error: str = ""

        # 对话执行器（惰性初始化）
        self._chat_executor: ChatExecutor | None = None

        # 确认对话框
        self._confirm_dialog = ConfirmDialog()
        self._pending_confirm_action: Callable[[], None] | None = None

        # 状态栏周期刷新
        self._status_refresh_time: float = 0.0
        self._status_refresh_interval: float = 10.0  # 10 秒刷新一次

        # 命令路由器
        self._command_router = self._build_command_router()

        # 输入历史
        self._input_history = InputHistory()

        # 主题
        self._current_theme: str = "dark"

    # ── 公共接口 ─────────────────────────────────────────────

    def _set_message(self, msg: str) -> None:
        """设置反馈消息并记录时间戳。"""
        self._last_message = msg
        self._message_time = time.monotonic()

    def run(self) -> None:
        """启动控制台主循环。"""
        self._running = True
        self._init_status()

        # 启动输入管理器
        self._input_manager.start()

        try:
            with Live(
                self._build_layout(),
                console=self._console,
                refresh_per_second=10,
                screen=False,
            ) as live:
                while self._running:
                    self._process_pending_input()
                    live.update(self._build_layout())
                    time.sleep(0.1)
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            self._running = False
            self._input_manager.stop()
            self._console.print("\n[info]已退出控制台[/]")

    # ── 输入处理 ─────────────────────────────────────────────

    def _process_pending_input(self) -> None:
        """处理输入队列中的按键（批量处理）。"""
        max_batch = 10  # 每帧最多处理 10 个按键
        for _ in range(max_batch):
            # 确认对话框优先
            if self._confirm_dialog.visible:
                key = self._input_manager.poll()
                if key:
                    self._confirm_dialog.handle_input(key)
                    if not self._confirm_dialog.visible:
                        if self._confirm_dialog.result and self._pending_confirm_action:
                            self._pending_confirm_action()
                        self._pending_confirm_action = None
                else:
                    break  # 队列空，退出循环
                continue

            key = self._input_manager.poll()

            if not key:
                break

            if key == "ctrl_c":
                if self._input_mode:
                    self._exit_input_mode()
                else:
                    self._running = False
                return  # 直接退出，不继续处理

            # 文本输入模式
            if self._input_mode:
                self._handle_input_mode(key)
                continue

            # 全局导航
            if key in ("up", "k"):
                self._tabs[self._active_tab_index].handle_input("up")
            elif key in ("down", "j"):
                self._tabs[self._active_tab_index].handle_input("down")
            elif key == "enter":
                self._tabs[self._active_tab_index].handle_input("enter")
            elif key == "escape":
                self._tabs[self._active_tab_index].handle_input("escape")
            elif key == "page_up":
                tab = self._tabs[self._active_tab_index]
                for _ in range(5):
                    tab.handle_input("up")
            elif key == "page_down":
                tab = self._tabs[self._active_tab_index]
                for _ in range(5):
                    tab.handle_input("down")
            elif key.startswith("char:"):
                ch = key[5:]
                if ch in ("1", "2", "3", "4", "5", "6", "7"):
                    idx = int(ch) - 1
                    if idx != self._active_tab_index:
                        self._tabs[self._active_tab_index].on_deactivate()
                        self._active_tab_index = idx
                        self._tabs[idx].on_activate()
                elif ch == "q":
                    self._running = False
                    return
                elif ch == "T":
                    new_name = next_theme()
                    self._current_theme = new_name
                    self._console = Console(theme=get_theme())
                    self._set_message(f"[info]主题已切换: {new_name}[/]")
                else:
                    self._dispatch_tab_cmd(ch)

    # ── 文本输入模式 ─────────────────────────────────────────

    def _enter_input_mode(self, prompt: str, callback: object) -> None:
        """进入文本输入模式。

        Args:
            prompt: 输入提示（如 "新会话名: "）。
            callback: 提交回调，接收输入文本。
        """
        self._input_mode = True
        self._input_buffer = ""
        self._input_prompt = prompt
        self._input_callback = callback  # type: ignore[assignment]

    def _exit_input_mode(self) -> None:
        """退出文本输入模式。"""
        self._input_mode = False
        self._input_buffer = ""
        self._input_prompt = ""
        self._input_callback = None

    def _handle_input_mode(self, key: str) -> None:
        """处理文本输入模式下的按键。"""
        if key == "enter":
            text = self._input_buffer.strip()
            if text:
                self._input_history.add(text)
                if self._input_callback:
                    self._input_callback(text)
            self._exit_input_mode()
            return

        if key == "escape":
            self._exit_input_mode()
            self._input_history.reset()
            self._set_message("[info]已取消[/]")
            return

        if key == "backspace":
            self._input_buffer = self._input_buffer[:-1]
            return

        if key == "up":
            prev = self._input_history.prev()
            if prev is not None:
                self._input_buffer = prev
            return

        if key == "down":
            nxt = self._input_history.next()
            self._input_buffer = nxt if nxt is not None else ""
            return

        if key.startswith("char:"):
            ch = key[5:]
            # 过滤控制字符，只接受可显示字符
            if ch and ord(ch) >= 32:
                self._input_buffer += ch
            return

    def _build_command_router(self) -> CommandRouter:
        """构建命令路由器，注册所有 Tab 命令。"""
        router = CommandRouter()

        # Chat Tab (0)
        router.register(
            0, "n", lambda: self._enter_input_mode("新会话名: ", self._create_session)
        )
        router.register(0, "d", self._cmd_chat_delete)
        router.register(0, "c", self._cmd_chat_send)

        # Tools Tab (1)
        router.register(1, "e", self._cmd_tools_toggle)
        router.register(1, "a", self._cmd_tools_filter)
        router.register(1, "t", self._cmd_tools_test)

        # Memory Tab (2)
        router.register(2, "d", self._cmd_memory_delete)
        router.register(2, "r", self._cmd_memory_rebuild)
        router.register(
            2, "/", lambda: self._enter_input_mode("搜索关键词: ", self._search_memory)
        )

        # Scheduler Tab (3)
        router.register(3, "p", self._cmd_scheduler_pause)
        router.register(3, "d", self._cmd_scheduler_delete)
        router.register(3, "l", self._cmd_scheduler_logs)
        router.register(3, "s", self._cmd_scheduler_toggle)

        # Stats Tab (4) — 子视图切换直接委托 handle_input
        router.register(4, "1", lambda: self._tabs[4].handle_input("1"))
        router.register(4, "2", lambda: self._tabs[4].handle_input("2"))
        router.register(4, "3", lambda: self._tabs[4].handle_input("3"))

        # Image Tab (5)
        router.register(5, "p", lambda: self._tabs[5].handle_input("p"))
        router.register(5, "d", self._cmd_image_delete)
        router.register(5, "o", lambda: self._tabs[5].handle_input("o"))

        # TTS Tab (6)
        router.register(6, "p", lambda: self._tabs[6].handle_input("p"))
        router.register(6, "s", lambda: self._tabs[6].handle_input("s"))
        router.register(6, "d", self._cmd_tts_delete)

        return router

    def _dispatch_tab_cmd(self, cmd: str) -> None:
        """分发 Tab 特定命令（通过 CommandRouter）。"""
        if not self._command_router.dispatch(self._active_tab_index, cmd):
            self._set_message(f"[warning]未知命令: {cmd}[/]")

    # ── Chat 命令处理器 ─────────────────────────────────────

    def _cmd_chat_delete(self) -> None:
        """删除当前会话。"""
        tab = self._tabs[0]

        def _do_delete() -> None:
            if tab.handle_input("d"):
                self._set_message("[success][OK] 已删除会话[/]")
            else:
                self._set_message("[warning]无可删除的会话[/]")

        self._confirm_dialog.show("确认删除当前会话？")
        self._pending_confirm_action = _do_delete

    def _cmd_chat_send(self) -> None:
        """进入聊天输入模式。"""
        if self._session_mgr.active_session is None:
            self._set_message("[warning]请先创建或选择会话[/]")
        elif self._chat_thinking:
            self._set_message("[warning]正在等待回复...[/]")
        else:
            self._enter_input_mode("消息: ", self._send_chat_message)

    # ── Tools 命令处理器 ────────────────────────────────────

    def _cmd_tools_toggle(self) -> None:
        """切换工具启用/禁用。"""
        if self._tabs[1].handle_input("e"):
            self._set_message("[success][OK] 状态已切换[/]")
        else:
            self._set_message("[warning]无法切换（核心工具不可禁用）[/]")

    def _cmd_tools_filter(self) -> None:
        """切换工具筛选。"""
        self._tabs[1].handle_input("a")
        self._set_message("[info]筛选已切换[/]")

    def _cmd_tools_test(self) -> None:
        """测试执行工具。"""
        if self._tabs[1].handle_input("t"):
            self._set_message("[success][OK] 工具测试中...[/]")
        else:
            self._set_message("[warning]无法测试该工具[/]")

    # ── Memory 命令处理器 ───────────────────────────────────

    def _cmd_memory_delete(self) -> None:
        """删除选中的记忆条目。"""
        tab = self._tabs[2]

        def _do_delete() -> None:
            if tab.handle_input("d"):
                self._set_message("[success][OK] 已删除记忆[/]")
            else:
                self._set_message("[warning]无可删除的记忆[/]")

        self._confirm_dialog.show("确认删除选中的记忆条目？")
        self._pending_confirm_action = _do_delete

    def _cmd_memory_rebuild(self) -> None:
        """重建记忆索引。"""
        self._tabs[2].handle_input("r")
        self._set_message("[success][OK] 索引已重建[/]")

    # ── Scheduler 命令处理器 ────────────────────────────────

    def _cmd_scheduler_pause(self) -> None:
        """暂停/恢复任务。"""
        if self._tabs[3].handle_input("p"):
            self._set_message("[success][OK] 状态已切换[/]")
        else:
            self._set_message("[warning]无法切换[/]")

    def _cmd_scheduler_delete(self) -> None:
        """删除选中的任务。"""
        tab = self._tabs[3]

        def _do_delete() -> None:
            if tab.handle_input("d"):
                self._set_message("[success][OK] 已删除任务[/]")
            else:
                self._set_message("[warning]无可删除的任务[/]")

        self._confirm_dialog.show("确认删除选中的任务？")
        self._pending_confirm_action = _do_delete

    def _cmd_scheduler_logs(self) -> None:
        """查看任务日志。"""
        self._tabs[3].handle_input("l")
        self._set_message("[info]查看日志（Esc 返回）[/]")

    def _cmd_scheduler_toggle(self) -> None:
        """切换调度器状态。"""
        self._tabs[3].handle_input("s")
        self._set_message("[info]调度器状态已切换[/]")

    # ── Image 命令处理器 ────────────────────────────────────

    def _cmd_image_delete(self) -> None:
        """删除选中的图像。"""
        tab = self._tabs[5]

        def _do_delete() -> None:
            if tab.handle_input("d"):
                self._set_message("[success][OK] 已删除图像[/]")
            else:
                self._set_message("[warning]无可删除的图像[/]")

        self._confirm_dialog.show("确认删除选中的图像？")
        self._pending_confirm_action = _do_delete

    # ── TTS 命令处理器 ─────────────────────────────────────

    def _cmd_tts_delete(self) -> None:
        """删除选中的音频。"""
        tab = self._tabs[6]

        def _do_delete() -> None:
            if tab.handle_input("d"):
                self._set_message("[success][OK] 已删除音频[/]")
            else:
                self._set_message("[warning]无可删除的音频[/]")

        self._confirm_dialog.show("确认删除选中的音频？")
        self._pending_confirm_action = _do_delete

    def _create_session(self, name: str) -> None:
        """创建会话回调（由输入模式调用）。"""
        try:
            self._session_mgr.create_session(session_id=name, name=name)
            self._set_message(f"[success][OK] 已创建会话: {name}[/]")
        except ValueError as e:
            self._set_message(f"[error][X] {e}[/]")

    def _send_chat_message(self, message: str) -> None:
        """发送聊天消息（由输入模式调用，在后台线程执行 LLM 调用）。"""
        active = self._session_mgr.active_session
        if active is None:
            self._set_message("[warning]无活跃会话[/]")
            return

        session_id = active.session_id
        with self._lock:
            self._chat_thinking = True
            self._chat_error = ""

        # 通知 ChatTab 显示用户消息和等待状态
        chat_tab: ChatTab = self._tabs[0]  # type: ignore[assignment]
        chat_tab.set_pending_user_message(message)

        def _run() -> None:
            try:
                import asyncio

                result = asyncio.run(self._do_chat(message, session_id))
                chat_tab.set_last_ai_response(result)
                self._session_mgr.refresh_message_count(session_id)
            except Exception as e:
                logger.exception("对话失败")
                with self._lock:
                    self._chat_error = str(e)
                chat_tab.set_last_ai_response(f"[调用失败: {e}]")
            finally:
                with self._lock:
                    self._chat_thinking = False

        threading.Thread(target=_run, daemon=True).start()

    async def _do_chat(self, user_input: str, session_id: str) -> str:
        """执行单轮对话（LLM + 工具循环）。"""
        if self._chat_executor is None:
            from src.ai.core.container import container

            self._chat_executor = ChatExecutor(container)

        result = await self._chat_executor.execute(user_input, session_id)
        return result.content

    def _search_memory(self, query: str) -> None:
        """搜索记忆回调（由输入模式调用）。"""
        memory_tab: MemoryTab = self._tabs[2]  # type: ignore[assignment]
        memory_tab.set_search_query(query)
        self._set_message(f"[info]搜索: {query}[/]")

    # ── 渲染 ─────────────────────────────────────────────────

    def _build_layout(self) -> Layout:
        """构建完整布局树。"""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=HEADER_HEIGHT),
            Layout(name="tab_bar", size=TAB_BAR_HEIGHT),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=FOOTER_HEIGHT),
        )

        # 周期性刷新状态栏（每 10 秒）
        now = time.monotonic()
        if now - self._status_refresh_time > self._status_refresh_interval:
            self._status_refresh_time = now
            self._refresh_status()

        # Header: 状态栏（实时更新会话名和 Tab 名称）
        width = self._console.width or 100
        active_session = self._session_mgr.active_session
        self._status_bar.session_name = active_session.name if active_session else ""
        self._status_bar.active_tab_name = self._tabs[self._active_tab_index].name
        layout["header"].update(self._status_bar.render(self._console, width))

        # Tab 标签行
        layout["tab_bar"].update(self._render_tab_bar(width))

        # Body: 三栏布局
        layout["body"].split_row(
            Layout(name="sidebar", ratio=SIDEBAR_RATIO, minimum_size=20),
            Layout(name="main", ratio=MAIN_RATIO, minimum_size=30),
            Layout(name="detail", ratio=DETAIL_RATIO, minimum_size=20),
        )

        active_tab = self._tabs[self._active_tab_index]

        # 侧边栏
        layout["sidebar"].update(self._render_sidebar(width // 4))

        # 主内容
        main_width = max(
            30, width * MAIN_RATIO // (SIDEBAR_RATIO + MAIN_RATIO + DETAIL_RATIO)
        )
        main_height = max(
            10, self._console.height - HEADER_HEIGHT - TAB_BAR_HEIGHT - FOOTER_HEIGHT
        )
        layout["main"].update(
            active_tab.render_content(self._console, main_width, main_height)
        )

        # 详情面板
        detail = active_tab.get_detail_panel(self._console, width // 4, main_height)
        if detail is None:
            detail = Panel(
                Text("  选择项目查看详情", style="muted"), border_style="border"
            )
        layout["detail"].update(detail)

        # Footer: 命令提示 + 反馈
        layout["footer"].update(self._render_footer(width))

        # 确认对话框叠加显示（仅覆盖 main 区域）
        if self._confirm_dialog.visible:
            dialog_panel = self._confirm_dialog.render(self._console)
            if dialog_panel is not None:
                layout["main"].update(Align.center(dialog_panel, vertical="middle"))

        return layout

    def _render_tab_bar(self, width: int) -> Text:
        """渲染 Tab 标签行。"""
        text = Text()
        for i, (hotkey, name, desc) in enumerate(_TAB_LABELS):
            if i == self._active_tab_index:
                text.append(f" [{hotkey}] {name} ", style="reverse bold")
            else:
                text.append(f" [{hotkey}] {name} ", style="muted")
            if i < len(_TAB_LABELS) - 1:
                text.append(" ")
        return text

    def _render_sidebar(self, width: int) -> Panel:
        """渲染侧边栏（使用 Tree 组织信息）。"""
        # 会话信息
        tree = Tree("[subtitle]会话信息[/]")
        active = self._session_mgr.active_session
        if active:
            tree.add(f"[active]{active.name}[/]")
            tree.add(f"[muted]{active.message_count} 条消息[/]")
        else:
            tree.add("[muted]无活跃会话[/]")

        # 对话状态（加锁读取共享状态）
        with self._lock:
            thinking = self._chat_thinking
            error = self._chat_error
        if thinking:
            frames = ["|", "/", "-", "\\"]
            frame = frames[int(time.monotonic() * 4) % 4]
            tree.add(f"[warning]{frame} AI 正在思考...[/]")
        if error:
            tree.add(f"[error]错误: {error[:40]}[/]")

        # 系统状态
        status_tree = Tree("[subtitle]系统状态[/]")
        # 实时统计摘要
        chat_tab = self._tabs[0]
        status_tree.add(f"[info]消息: {len(chat_tab._messages)}[/]")  # type: ignore[attr-defined]

        # 工具数
        try:
            tools_tab = self._tabs[1]
            tools_tab._ensure_cache()  # type: ignore[attr-defined]
            status_tree.add(f"[info]工具: {len(tools_tab._tools)}[/]")  # type: ignore[attr-defined]
        except Exception:
            status_tree.add("[muted]工具: -[/]")

        # 记忆数
        status_tree.add(f"[info]记忆: {self._status_bar.memory_count}[/]")

        # 快捷键
        shortcuts_tree = Tree("[subtitle]快捷键[/]")
        shortcuts = [
            ("1-7", "切换 Tab"),
            ("N", "新建会话"),
            ("C", "发送消息"),
            ("D", "删除"),
            ("T", "切换主题"),
            ("Enter", "激活会话"),
            ("UP/DN", "导航"),
            ("Q", "退出"),
        ]
        for key, desc in shortcuts:
            shortcuts_tree.add(f"[key]{key}[/] [muted]{desc}[/]")

        # 组合所有子树
        root = Tree("[title]信息[/]")
        root.add(tree)
        root.add(status_tree)
        root.add(shortcuts_tree)

        return Panel(
            root,
            border_style="border",
            width=min(width, 24),
        )

    def _render_footer(self, width: int) -> Panel:
        """渲染底部命令提示。"""
        text = Text()

        # 文本输入模式：显示输入框
        if self._input_mode:
            text.append(f" {self._input_prompt}", style="key")
            text.append(f"{self._input_buffer}", style="active")
            text.append("_", style="active blink")
            text.append("\n")
            text.append(" Enter 确认 | Esc 取消", style="muted")
            return Panel(text, border_style="border")

        # 普通模式：显示命令提示
        commands: list[tuple[str, str]] = [("1-5", "Tab"), ("q", "退出")]

        # 使用 Tab 的 get_footer_commands 获取命令列表
        tab = self._tabs[self._active_tab_index]
        tab_commands = tab.get_footer_commands()
        commands += tab_commands

        commands += [("UP/DN", "导航"), ("PgUp/Dn", "翻页")]

        for key, desc in commands:
            text.append(f" {key}", style="key")
            text.append(f"={desc}", style="muted")

        # 反馈消息（超过 5 秒自动清除）
        if self._last_message:
            if self._message_time and (time.monotonic() - self._message_time) > 5.0:
                self._last_message = ""
            else:
                text.append(f"\n  {self._last_message}")

        return Panel(text, border_style="border")

    # ── 初始化 ───────────────────────────────────────────────

    def _init_status(self) -> None:
        """初始化状态栏信息。"""
        try:
            from src.ai.core.container import container

            # 模型名称
            try:
                model_svc = container.model_container.model_service()
                self._status_bar.model_name = getattr(
                    model_svc, "default_model", "未配置"
                )
            except Exception:
                self._status_bar.model_name = "未配置"

            # 调度器状态
            try:
                scheduler_svc = container.scheduler_container.scheduler_service()
                self._status_bar.scheduler_running = scheduler_svc.is_running
            except Exception:
                self._status_bar.scheduler_running = False

            # 记忆条数
            try:
                memory_svc = container.memory_container.memory_service()
                stats = memory_svc.get_stats()
                self._status_bar.memory_count = stats.get("total", 0)
            except Exception:
                self._status_bar.memory_count = 0

            # 工具数
            try:
                registry = container.tool_container.tool_registry()
                self._status_bar.tool_count = len(registry.list(enabled_only=False))
            except Exception:
                self._status_bar.tool_count = 0

            # 会话
            self._session_mgr.discover_existing_sessions()
            if self._session_mgr.active_session:
                self._status_bar.session_name = self._session_mgr.active_session.name

            # 活跃 Tab 名称
            self._status_bar.active_tab_name = self._tabs[self._active_tab_index].name

        except Exception as e:
            logger.debug("初始化状态失败: %s", e)

    def _refresh_status(self) -> None:
        """周期性刷新状态栏信息。"""
        try:
            from src.ai.core.container import container

            try:
                scheduler_svc = container.scheduler_container.scheduler_service()
                self._status_bar.scheduler_running = scheduler_svc.is_running
            except Exception:
                pass

            try:
                memory_svc = container.memory_container.memory_service()
                stats = memory_svc.get_stats()
                self._status_bar.memory_count = stats.get("total", 0)
            except Exception:
                pass

            try:
                registry = container.tool_container.tool_registry()
                self._status_bar.tool_count = len(registry.list(enabled_only=False))
            except Exception:
                pass

            # 更新活跃 Tab 名称
            self._status_bar.active_tab_name = self._tabs[self._active_tab_index].name

        except Exception:
            pass
