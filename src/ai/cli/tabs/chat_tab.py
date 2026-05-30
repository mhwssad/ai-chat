"""对话管理面板 — 消息历史、输入、上下文信息。"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.sessions import SessionManager
from src.ai.cli.tabs import BaseTab
from src.ai.cli.utils.theme import Icons
from src.ai.cli.utils.formatting import truncate


class ChatTab(BaseTab):
    """对话管理面板。

    展示消息列表和会话信息，支持消息浏览。
    """

    name = "对话"
    hotkey = "1"

    def __init__(self, session_mgr: SessionManager) -> None:
        super().__init__()
        self._session_mgr = session_mgr
        self._messages: list[dict[str, str]] = []

    def _load_messages(self) -> None:
        """加载当前会话的消息。"""
        active = self._session_mgr.active_session
        if active is None:
            self._messages = []
            return

        try:
            messages = self._session_mgr.history_manager.get_messages(active.session_id)
            self._messages = []
            for msg in messages:
                self._messages.append(
                    {
                        "role": msg.type,
                        "content": str(msg.content),
                    }
                )
        except Exception:
            self._messages = []

    def render_content(self, console: Console, width: int, height: int) -> Panel:
        self._load_messages()
        sessions = self._session_mgr.list_sessions()
        self._clamp_selection(len(sessions))

        text = Text()

        # 会话列表
        text.append(f"会话列表 ({len(sessions)} 个)\n", style="subtitle")
        text.append(Icons.LINE * (width - 4) + "\n", style="muted")

        if not sessions:
            text.append("  暂无会话，按 N 创建新会话\n", style="muted")
        else:
            for i, s in enumerate(sessions):
                prefix = Icons.POINTER if i == self._selected_index else " "
                active_icon = Icons.ACTIVE if s.is_active else Icons.INACTIVE
                style = "selected" if i == self._selected_index else ""
                text.append(f" {prefix} {active_icon} {s.name}", style=style)
                text.append(f" ({s.message_count} 条)\n", style="muted")

        # 消息历史
        text.append("\n", style="")
        text.append("消息历史\n", style="subtitle")
        text.append(Icons.LINE * (width - 4) + "\n", style="muted")

        if not self._messages:
            text.append("  暂无消息\n", style="muted")
        else:
            # 显示最近消息（留出空间给 header + footer）
            max_display = max(1, height - 12)
            recent = self._messages[-max_display:]
            for msg in recent:
                role = msg["role"]
                content = truncate(msg["content"], max_len=width - 12)
                if role == "human":
                    text.append(f"  你: {content}\n", style="info")
                elif role == "ai":
                    text.append(f"  助手: {content}\n", style="value")
                elif role == "tool":
                    text.append(f"  [工具] {content}\n", style="muted")
                else:
                    text.append(f"  [{role}] {content}\n", style="muted")

        return Panel(
            text, title=f"[title]{Icons.TAB_CHAT} 对话[/]", border_style="border"
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
            # 切换到选中会话
            if sessions and self._selected_index < len(sessions):
                target = sessions[self._selected_index]
                self._session_mgr.switch_session(target.session_id)
            return True
        return False

    def get_detail_panel(self, console: Console, width: int, height: int) -> Panel:
        active = self._session_mgr.active_session
        text = Text()

        if active is None:
            text.append("  无活跃会话", style="muted")
        else:
            text.append("会话详情\n\n", style="subtitle")
            text.append(f"  ID: {active.session_id}\n", style="value")
            text.append(f"  名称: {active.name}\n", style="value")
            text.append(f"  消息数: {active.message_count}\n", style="value")
            text.append(
                f"  状态: {'活跃' if active.is_active else '非活跃'}\n",
                style="active" if active.is_active else "inactive",
            )

            # 上下文统计
            text.append("\n上下文信息\n", style="subtitle")
            try:
                self._load_messages()
                text.append(f"  总消息: {len(self._messages)}\n", style="value")

                user_count = sum(1 for m in self._messages if m["role"] == "human")
                ai_count = sum(1 for m in self._messages if m["role"] == "ai")
                tool_count = sum(1 for m in self._messages if m["role"] == "tool")
                text.append(f"  用户消息: {user_count}\n", style="value")
                text.append(f"  助手消息: {ai_count}\n", style="value")
                text.append(f"  工具调用: {tool_count}\n", style="value")
            except Exception:
                text.append("  无法加载详情\n", style="muted")

        return Panel(text, title="[title]上下文[/]", border_style="border")
