"""TUI 控制台 — Rich Layout + Live 渲染 + msvcrt 键盘输入。

采用 Rich Live 实时刷新 + Layout 分栏布局。
Windows 下使用 msvcrt 实现方向键、翻页等原生键盘支持。
"""

import collections
import json
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

from src.ai.cli.sessions import SessionManager
from src.ai.cli.tabs import BaseTab
from src.ai.cli.tabs.chat_tab import ChatTab
from src.ai.cli.tabs.memory_tab import MemoryTab
from src.ai.cli.tabs.scheduler_tab import SchedulerTab
from src.ai.cli.tabs.tools_tab import ToolsTab
from src.ai.cli.utils.theme import THEME
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

_TAB_NAMES = ["chat", "tools", "memory", "scheduler"]
_TAB_LABELS = [
    ("1", "Chat", "对话管理"),
    ("2", "Tools", "工具管理"),
    ("3", "Memory", "记忆管理"),
    ("4", "Scheduler", "任务管理"),
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
        ]
        self._active_tab_index: int = 0
        self._status_bar = StatusBar()
        self._running: bool = False
        self._last_message: str = ""
        self._message_time: float = 0.0
        self._scroll_offset: int = 0
        self._input_queue: collections.deque[str] = collections.deque(maxlen=64)
        self._lock = threading.Lock()
        self._input_thread: threading.Thread | None = None

        # 文本输入模式（用于 n 新建会话、/ 搜索、聊天等）
        self._input_mode: bool = False
        self._input_buffer: str = ""
        self._input_prompt: str = ""
        self._input_callback: Callable[[str], None] | None = None

        # 对话状态
        self._chat_thinking: bool = False
        self._chat_error: str = ""

        # 确认对话框
        self._confirm_dialog = ConfirmDialog()
        self._pending_confirm_action: Callable[[], None] | None = None

        # 状态栏周期刷新
        self._status_refresh_time: float = 0.0
        self._status_refresh_interval: float = 10.0  # 10 秒刷新一次

    # ── 公共接口 ─────────────────────────────────────────────

    def _set_message(self, msg: str) -> None:
        """设置反馈消息并记录时间戳。"""
        self._last_message = msg
        self._message_time = time.monotonic()

    def run(self) -> None:
        """启动控制台主循环。"""
        self._running = True
        self._init_status()

        # 启动输入线程
        self._input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self._input_thread.start()

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
            self._console.print("\n[info]已退出控制台[/]")

    # ── 输入线程 ─────────────────────────────────────────────

    def _input_loop(self) -> None:
        """输入线程：msvcrt 逐字符读取。"""
        try:
            import msvcrt
        except ImportError:
            # 非 Windows：回退到 select + stdin
            self._input_loop_unix()
            return

        while self._running:
            try:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()

                    # 处理特殊键前缀
                    if ch in ("\x00", "\xe0"):
                        ch2 = msvcrt.getwch()
                        key = self._translate_special(ch2)
                        with self._lock:
                            self._input_queue.append(key)
                    elif ch == "\x1b":
                        # Escape 或 VT 序列
                        key = self._read_escape_seq()
                        with self._lock:
                            self._input_queue.append(key)
                    elif ch in ("\r", "\n"):
                        with self._lock:
                            self._input_queue.append("enter")
                    elif ch == "\x03":  # Ctrl+C
                        with self._lock:
                            self._input_queue.append("ctrl_c")
                    elif ch == "\x08":  # Backspace
                        with self._lock:
                            self._input_queue.append("backspace")
                    else:
                        with self._lock:
                            self._input_queue.append(f"char:{ch}")
                else:
                    time.sleep(0.02)
            except Exception as e:
                logger.debug("输入线程异常: %s", e)
                time.sleep(0.1)

    def _input_loop_unix(self) -> None:
        """Unix 回退输入（非阻塞 stdin）。"""
        import select
        import sys
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while self._running:
                if select.select([sys.stdin], [], [], 0.05)[0]:
                    ch = sys.stdin.read(1)
                    if ch == "\x1b":
                        rest = ""
                        if select.select([sys.stdin], [], [], 0.02)[0]:
                            rest = sys.stdin.read(2)
                        if rest == "[A":
                            with self._lock:
                                self._input_queue.append("up")
                        elif rest == "[B":
                            with self._lock:
                                self._input_queue.append("down")
                        elif rest == "[C":
                            with self._lock:
                                self._input_queue.append("right")
                        elif rest == "[D":
                            with self._lock:
                                self._input_queue.append("left")
                        elif rest == "[H":
                            with self._lock:
                                self._input_queue.append("home")
                        elif rest == "[F":
                            with self._lock:
                                self._input_queue.append("end")
                        elif (
                            rest
                            and len(rest) == 2
                            and rest[0] == "["
                            and rest[1] in "123456"
                        ):
                            # 长序列：读取 ~ 尾缀
                            code = rest[1]
                            if select.select([sys.stdin], [], [], 0.02)[0]:
                                sys.stdin.read(1)  # 消耗 ~
                            long_map = {
                                "1": "home",
                                "2": "insert",
                                "3": "delete",
                                "4": "end",
                                "5": "page_up",
                                "6": "page_down",
                            }
                            with self._lock:
                                self._input_queue.append(
                                    long_map.get(code, f"vt:{code}")
                                )
                        else:
                            with self._lock:
                                self._input_queue.append("escape")
                    elif ch in ("\r", "\n"):
                        with self._lock:
                            self._input_queue.append("enter")
                    elif ch == "\x03":
                        with self._lock:
                            self._input_queue.append("ctrl_c")
                    elif ch == "\x7f":
                        with self._lock:
                            self._input_queue.append("backspace")
                    else:
                        with self._lock:
                            self._input_queue.append(f"char:{ch}")
                else:
                    time.sleep(0.02)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _translate_special(self, ch: str) -> str:
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

    def _read_escape_seq(self) -> str:
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
                        # 对所有 1-6 的 code 统一消耗 ~ 尾缀
                        if code in ("1", "2", "3", "4", "5", "6") and msvcrt.kbhit():
                            msvcrt.getwch()
                        return result
                return f"esc_seq:{ch}"
        except Exception:
            pass
        return "escape"

    # ── 输入处理 ─────────────────────────────────────────────

    def _process_pending_input(self) -> None:
        """处理输入队列中的按键（批量处理）。"""
        max_batch = 10  # 每帧最多处理 10 个按键
        for _ in range(max_batch):
            # 确认对话框优先
            if self._confirm_dialog.visible:
                with self._lock:
                    key = self._input_queue.popleft() if self._input_queue else ""
                if key:
                    self._confirm_dialog.handle_input(key)
                    if not self._confirm_dialog.visible:
                        if self._confirm_dialog.result and self._pending_confirm_action:
                            self._pending_confirm_action()
                        self._pending_confirm_action = None
                else:
                    break  # 队列空，退出循环
                continue

            with self._lock:
                key = self._input_queue.popleft() if self._input_queue else ""

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
                if ch in ("1", "2", "3", "4"):
                    idx = int(ch) - 1
                    if idx != self._active_tab_index:
                        self._tabs[self._active_tab_index].on_deactivate()
                        self._active_tab_index = idx
                        self._tabs[idx].on_activate()
                elif ch == "q":
                    self._running = False
                    return
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
        self._input_callback = callback

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
            if text and self._input_callback:
                self._input_callback(text)
            self._exit_input_mode()
            return

        if key == "escape":
            self._exit_input_mode()
            self._set_message("[info]已取消[/]")
            return

        if key == "backspace":
            self._input_buffer = self._input_buffer[:-1]
            return

        if key.startswith("char:"):
            ch = key[5:]
            # 过滤控制字符，只接受可显示字符
            if ch and ord(ch) >= 32:
                self._input_buffer += ch
            return

    def _dispatch_tab_cmd(self, cmd: str) -> None:
        """分发 Tab 特定命令。"""
        idx = self._active_tab_index
        tab = self._tabs[idx]

        if idx == 0:  # Chat
            self._dispatch_chat(cmd, tab)
        elif idx == 1:  # Tools
            self._dispatch_tools(cmd, tab)
        elif idx == 2:  # Memory
            self._dispatch_memory(cmd, tab)
        elif idx == 3:  # Scheduler
            self._dispatch_scheduler(cmd, tab)

    def _dispatch_chat(self, cmd: str, tab: BaseTab) -> None:
        """对话 Tab 命令。"""
        if cmd == "n":
            self._enter_input_mode("新会话名: ", self._create_session)
        elif cmd == "d":
            # 使用确认对话框
            def _do_delete() -> None:
                if tab.handle_input("d"):
                    self._set_message("[success][OK] 已删除会话[/]")
                else:
                    self._set_message("[warning]无可删除的会话[/]")

            self._confirm_dialog.show("确认删除当前会话？")
            self._pending_confirm_action = _do_delete
        elif cmd == "c":
            # 进入聊天输入模式
            if self._session_mgr.active_session is None:
                self._set_message("[warning]请先创建或选择会话[/]")
            elif self._chat_thinking:
                self._set_message("[warning]正在等待回复...[/]")
            else:
                self._enter_input_mode("消息: ", self._send_chat_message)
        else:
            self._set_message(f"[warning]未知命令: {cmd}[/]")

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
        from src.ai.core.container import container

        memory_svc = container.memory_container.memory_service()
        context_svc = container.context_container.context_service()
        chat_llm = container.chat_llm()
        chat_cfg = container.chat_model_config()
        tool_mgr = container.tool_container.tool_manager()

        tools = tool_mgr.list_tools(enabled_only=True)

        # 复用 main.py 的 _chat_once 逻辑
        from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

        from src.ai.core.context import ContextBuildRequest

        # 构建上下文
        request = ContextBuildRequest(
            messages=[HumanMessage(content=user_input)],
            model_config=chat_cfg,
            session_id=session_id,
            enable_memory=True,
            enable_tools=True,
            enable_rag=False,
        )
        result = await context_svc.abuild(request)

        # 绑定工具并调用 LLM
        llm_with_tools = chat_llm.bind_tools(tools)
        response: AIMessage = await llm_with_tools.ainvoke(result.messages)

        # 工具调用循环
        messages = list(result.messages)
        new_messages: list[AIMessage | ToolMessage] = []  # 仅保存本轮新增消息
        max_rounds = 10
        round_count = 0
        while response.tool_calls and round_count < max_rounds:
            round_count += 1
            messages.append(response)
            new_messages.append(response)  # 保存含 tool_calls 的 AIMessage

            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["args"]
                tool_id = tc["id"]

                try:
                    tool_result = await tool_mgr.execute(tool_name, tool_args)
                    result_str = (
                        tool_result
                        if isinstance(tool_result, str)
                        else json.dumps(tool_result, ensure_ascii=False, default=str)
                    )
                    if len(result_str) > 2000:
                        result_str = result_str[:2000] + "\n...(已截断)"
                except Exception as e:
                    result_str = f"工具执行失败: {e}"

                tool_msg = ToolMessage(content=result_str, tool_call_id=tool_id)
                messages.append(tool_msg)
                new_messages.append(tool_msg)

            response = await llm_with_tools.ainvoke(messages)

        # 保存历史（仅本轮新增消息，避免重复保存旧历史中的 ToolMessage）
        history_mgr = container.context_container.chat_history_manager()
        history_mgr.add_message(session_id, HumanMessage(content=user_input))
        for msg in new_messages:
            history_mgr.add_message(session_id, msg)
        history_mgr.add_message(session_id, response)

        # 提取记忆
        try:
            candidates = await memory_svc.aextract_from_conversation(
                user_input, response.content
            )
            if candidates:
                memory_svc.save_extracted(candidates, session_id=session_id)
        except Exception:
            pass

        return response.content

    def _search_memory(self, query: str) -> None:
        """搜索记忆回调（由输入模式调用）。"""
        memory_tab: MemoryTab = self._tabs[2]  # type: ignore[assignment]
        memory_tab.set_search_query(query)
        self._set_message(f"[info]搜索: {query}[/]")

    def _dispatch_tools(self, cmd: str, tab: BaseTab) -> None:
        """工具 Tab 命令。"""
        if cmd == "e":
            if tab.handle_input("e"):
                self._set_message("[success][OK] 状态已切换[/]")
            else:
                self._set_message("[warning]无法切换（核心工具不可禁用）[/]")
        elif cmd == "a":
            tab.handle_input("a")
            self._set_message("[info]筛选已切换[/]")
        elif cmd == "t":
            if tab.handle_input("t"):
                self._set_message("[success][OK] 工具测试中...[/]")
            else:
                self._set_message("[warning]无法测试该工具[/]")
        else:
            self._set_message(f"[warning]未知命令: {cmd}[/]")

    def _dispatch_memory(self, cmd: str, tab: BaseTab) -> None:
        """记忆 Tab 命令。"""
        if cmd == "d":
            # 使用确认对话框
            def _do_delete() -> None:
                if tab.handle_input("d"):
                    self._set_message("[success][OK] 已删除记忆[/]")
                else:
                    self._set_message("[warning]无可删除的记忆[/]")

            self._confirm_dialog.show("确认删除选中的记忆条目？")
            self._pending_confirm_action = _do_delete
        elif cmd == "r":
            tab.handle_input("r")
            self._set_message("[success][OK] 索引已重建[/]")
        elif cmd == "/":
            self._enter_input_mode("搜索关键词: ", self._search_memory)
        else:
            self._set_message(f"[warning]未知命令: {cmd}[/]")

    def _dispatch_scheduler(self, cmd: str, tab: BaseTab) -> None:
        """定时任务 Tab 命令。"""
        if cmd == "p":
            if tab.handle_input("p"):
                self._set_message("[success][OK] 状态已切换[/]")
            else:
                self._set_message("[warning]无法切换[/]")
        elif cmd == "d":
            # 使用确认对话框
            def _do_delete() -> None:
                if tab.handle_input("d"):
                    self._set_message("[success][OK] 已删除任务[/]")
                else:
                    self._set_message("[warning]无可删除的任务[/]")

            self._confirm_dialog.show("确认删除选中的任务？")
            self._pending_confirm_action = _do_delete
        elif cmd == "l":
            tab.handle_input("l")
            self._set_message("[info]查看日志（Esc 返回）[/]")
        elif cmd == "s":
            tab.handle_input("s")
            self._set_message("[info]调度器状态已切换[/]")
        else:
            self._set_message(f"[warning]未知命令: {cmd}[/]")

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

        # Header: 状态栏（实时更新会话名）
        width = self._console.width or 100
        active_session = self._session_mgr.active_session
        self._status_bar.session_name = active_session.name if active_session else ""
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
                layout["main"].update(
                    Align.center(dialog_panel, vertical="middle")
                )

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
        """渲染侧边栏（系统信息 + 快捷键）。"""
        text = Text()

        # 活跃会话
        active = self._session_mgr.active_session
        text.append("当前会话\n", style="subtitle")
        if active:
            text.append(f"  {active.name}\n", style="active")
            text.append(f"  {active.message_count} 条消息\n", style="muted")
        else:
            text.append("  无\n", style="muted")

        # 对话状态（加锁读取共享状态）
        with self._lock:
            thinking = self._chat_thinking
            error = self._chat_error
        if thinking:
            text.append("\n")
            dots = "." * (int(time.monotonic() * 2) % 4)
            text.append(f"  [AI] 正在思考{dots}\n", style="warning")
        if error:
            text.append("\n")
            text.append(f"  [错误] {error[:60]}\n", style="error")

        # 快捷键
        text.append("\n")
        text.append("快捷键\n", style="subtitle")
        shortcuts = [
            ("1-4", "切换 Tab"),
            ("N", "新建会话"),
            ("C", "发送消息"),
            ("D", "删除"),
            ("Enter", "激活会话"),
            ("UP/DN", "导航"),
            ("Q", "退出"),
        ]
        for key, desc in shortcuts:
            text.append(f"  {key}", style="key")
            text.append(f" {desc}\n", style="muted")

        return Panel(
            text,
            title="[title]信息[/]",
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
        commands: list[tuple[str, str]] = [("1-4", "Tab"), ("q", "退出")]

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
                # 尝试获取默认模型配置
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

            # 会话
            self._session_mgr.discover_existing_sessions()
            if self._session_mgr.active_session:
                self._status_bar.session_name = self._session_mgr.active_session.name

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
        except Exception:
            pass
