"""对话管理面板 — 消息历史、输入、上下文信息。"""

import logging

from rich.console import Console
from rich.group import Group
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.sessions import SessionManager
from src.ai.cli.tabs import BaseTab
from src.ai.cli.utils.theme import Icons
from src.ai.cli.utils.formatting import truncate
from src.ai.cli.utils.markdown_renderer import render_markdown
from src.ai.cli.widgets.spinner import Spinner

logger = logging.getLogger(__name__)


class ChatTab(BaseTab):
    """对话管理面板。

    展示消息列表和会话信息，支持会话切换和删除。
    """

    name = "对话"
    hotkey = "1"

    def __init__(self, session_mgr: SessionManager) -> None:
        super().__init__()
        self._session_mgr = session_mgr
        self._messages: list[dict[str, str]] = []
        self._pending_user_message: str = ""
        self._thinking: bool = False
        self._spinner: Spinner = Spinner("AI 正在思考")

    def _load_data(self) -> None:
        """加载当前会话的消息。"""
        active = self._session_mgr.active_session
        if active is None:
            self._messages = []
            return

        try:
            messages = self._session_mgr.history_manager.get_messages(active.session_id)
            self._messages = [
                {"role": msg.type, "content": str(msg.content)}
                for msg in messages
                if msg.type not in ("system", "generic")
            ]
        except Exception as e:
            logger.debug("加载消息失败: %s", e)
            self._messages = []

    def set_pending_user_message(self, message: str) -> None:
        """设置待发送的用户消息（显示在消息列表末尾）。"""
        self._pending_user_message = message
        self._thinking = True
        self._invalidate_cache()

    def set_last_ai_response(self, response: str) -> None:
        """设置 AI 回复（清除待发送状态）。"""
        self._pending_user_message = ""
        self._thinking = False
        self._invalidate_cache()

    def render_content(self, console: Console, width: int, height: int) -> Panel:
        # 活跃会话标题
        active = self._session_mgr.active_session
        if active:
            header = Text()
            header.append(f" {active.name}", style="active")
            header.append(f" ({active.message_count} 条消息)\n", style="muted")
        else:
            header = Text()
            header.append(" 无活跃会话\n", style="muted")
            header.append("  按 N 新建会话，或按 Enter 激活选中会话\n", style="muted")
            return Panel(
                header, title=f"[title]{Icons.TAB_CHAT} 对话[/]", border_style="border"
            )

        # 消息渲染列表
        renderables: list[object] = [header]

        # 消息历史（占满可用空间）
        self._ensure_cache()
        if not self._messages and not self._pending_user_message:
            empty = Text()
            empty.append("  暂无消息\n", style="muted")
            empty.append("  按 C 发送消息\n", style="muted")
            renderables.append(empty)
        else:
            max_display = max(1, height - 6)
            recent = self._messages[-max_display:]
            for msg in recent:
                role = msg["role"]
                content = msg["content"]
                if role == "human":
                    # 用户消息：带边框样式
                    t = Text()
                    t.append("  ┌─ 你 ──────────────────────\n", style="info")
                    t.append(
                        f"  │ {truncate(content, max_len=width - 12)}\n", style="info"
                    )
                    t.append("  └───────────────────────────\n", style="info")
                    renderables.append(t)
                elif role == "ai":
                    # AI 消息：Markdown 渲染
                    header_t = Text()
                    header_t.append("  ┌─ 助手 ────────────────────\n", style="active")
                    renderables.append(header_t)
                    # 内容使用 Markdown 渲染
                    md_content = render_markdown(content, width=max(20, width - 6))
                    renderables.append(md_content)
                    footer_t = Text()
                    footer_t.append("  └───────────────────────────\n", style="active")
                    renderables.append(footer_t)
                elif role == "tool":
                    # 工具消息折叠：仅显示工具名+状态
                    t = Text()
                    tool_name = content.split(":")[0] if ":" in content else content
                    t.append(f"  [工具] {truncate(tool_name, 30)}\n", style="muted")
                    renderables.append(t)
                else:
                    t = Text()
                    t.append(
                        f"  [{role}] {truncate(content, max_len=width - 12)}\n",
                        style="muted",
                    )
                    renderables.append(t)

            # 显示待发送的用户消息
            if self._pending_user_message:
                content = truncate(self._pending_user_message, max_len=width - 12)
                t = Text()
                t.append("  ┌─ 你 ──────────────────────\n", style="info")
                t.append(f"  │ {content}\n", style="info")
                t.append("  └───────────────────────────\n", style="info")
                renderables.append(t)

            # 显示思考状态（Spinner 动画）
            if self._thinking:
                t = Text()
                t.append("  ┌─ 助手 ────────────────────\n", style="warning")
                t.append("  │ ")
                t.append_text(self._spinner.render())
                t.append("\n")
                t.append("  └───────────────────────────\n", style="warning")
                renderables.append(t)

        return Panel(
            Group(*renderables),
            title=f"[title]{Icons.TAB_CHAT} 对话[/]",
            border_style="border",
        )

    def handle_input(self, key: str) -> bool:
        sessions = self._session_mgr.list_sessions()

        if key == "up":
            self._move_selection(-1, len(sessions))
            return True
        elif key == "down":
            self._move_selection(1, len(sessions))
            return True
        elif key == "enter":
            if sessions and self._selected_index < len(sessions):
                target = sessions[self._selected_index]
                self._session_mgr.switch_session(target.session_id)
            return True
        elif key == "d":
            return self._delete_selected(sessions)
        return False

    @property
    def is_chat_ready(self) -> bool:
        """是否有活跃会话可以聊天。"""
        return self._session_mgr.active_session is not None

    def _delete_selected(self, sessions: list) -> bool:
        """删除选中的会话。"""
        if not sessions or self._selected_index >= len(sessions):
            return False
        target = sessions[self._selected_index]
        try:
            self._session_mgr.delete_session(target.session_id)
            self._selected_index = max(0, self._selected_index - 1)
            self._invalidate_cache()
            return True
        except Exception as e:
            logger.debug("删除会话失败: %s", e)
            return False

    def get_footer_commands(self) -> list[tuple[str, str]]:
        """返回 Chat Tab 底部命令列表。"""
        return [("n", "新建会话"), ("c", "发送消息"), ("d", "删除")]

    def get_detail_panel(self, console: Console, width: int, height: int) -> Panel:
        sessions = self._session_mgr.list_sessions()
        active = self._session_mgr.active_session
        text = Text()

        # 会话选择列表
        text.append("会话切换\n", style="subtitle")
        text.append(Icons.LINE * (width - 4) + "\n", style="muted")

        if not sessions:
            text.append("  暂无会话\n", style="muted")
            text.append("  按 N 新建\n", style="muted")
        else:
            visible = max(1, height - 10)
            scroll = self._get_scroll_offset(visible, len(sessions))
            for i in range(scroll, min(scroll + visible, len(sessions))):
                s = sessions[i]
                prefix = Icons.POINTER if i == self._selected_index else " "
                active_icon = Icons.ACTIVE if s.is_active else Icons.INACTIVE
                style = "selected" if i == self._selected_index else ""
                text.append(f" {prefix} {active_icon} {s.name}", style=style)
                text.append(f" ({s.message_count})\n", style="muted")

        # 活跃会话统计
        if active:
            text.append("\n")
            text.append("上下文统计\n", style="subtitle")
            text.append(f"  总消息: {len(self._messages)}\n", style="value")
            user_count = sum(1 for m in self._messages if m["role"] == "human")
            ai_count = sum(1 for m in self._messages if m["role"] == "ai")
            tool_count = sum(1 for m in self._messages if m["role"] == "tool")
            text.append(f"  用户: {user_count}\n", style="value")
            text.append(f"  助手: {ai_count}\n", style="value")
            text.append(f"  工具: {tool_count}\n", style="value")

        return Panel(text, title="[title]会话[/]", border_style="border")
