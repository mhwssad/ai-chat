"""多会话管理器 — 管理并行对话会话的生命周期。"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.ai.core.memory.history import ChatHistoryManager


@dataclass
class SessionInfo:
    """会话信息。"""

    session_id: str
    name: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message_count: int = 0
    is_active: bool = False
    metadata: dict[str, object] = field(default_factory=dict)


class SessionManager:
    """多会话管理器。

    职责：
    - 创建 / 切换 / 删除会话
    - 发现已有的历史会话
    - 委托 ChatHistoryManager 持久化消息

    Attributes:
        _history_mgr: 聊天历史管理器（负责实际持久化）。
        _sessions: 会话信息字典（session_id → SessionInfo）。
        _active_id: 当前活跃会话 ID。
    """

    def __init__(self, history_mgr: ChatHistoryManager) -> None:
        self._history_mgr = history_mgr
        self._sessions: dict[str, SessionInfo] = {}
        self._active_id: str | None = None

    # ── 查询 ────────────────────────────────────────────────

    @property
    def active_session(self) -> SessionInfo | None:
        """当前活跃会话。"""
        if self._active_id is None:
            return None
        return self._sessions.get(self._active_id)

    @property
    def active_session_id(self) -> str | None:
        """当前活跃会话 ID。"""
        return self._active_id

    def list_sessions(self) -> list[SessionInfo]:
        """列出所有会话（按创建时间降序）。"""
        return sorted(self._sessions.values(), key=lambda s: s.created_at, reverse=True)

    def get_session(self, session_id: str) -> SessionInfo | None:
        """获取指定会话信息。"""
        return self._sessions.get(session_id)

    # ── 创建 ────────────────────────────────────────────────

    def create_session(
        self,
        session_id: str | None = None,
        name: str | None = None,
        activate: bool = True,
    ) -> SessionInfo:
        """创建新会话。

        Args:
            session_id: 会话 ID，默认自动生成。
            name: 显示名称，默认使用 session_id。
            activate: 是否立即切换到新会话。

        Returns:
            新创建的 SessionInfo。

        Raises:
            ValueError: session_id 已存在。
        """
        if session_id is None:
            count = len(self._sessions) + 1
            session_id = f"session-{count}"
        if session_id in self._sessions:
            raise ValueError(f"会话 '{session_id}' 已存在")

        info = SessionInfo(
            session_id=session_id,
            name=name or session_id,
        )
        self._sessions[session_id] = info

        if activate:
            self.switch_session(session_id)

        return info

    # ── 切换 ────────────────────────────────────────────────

    def switch_session(self, session_id: str) -> SessionInfo:
        """切换活跃会话。

        Args:
            session_id: 目标会话 ID。

        Returns:
            切换后的 SessionInfo。

        Raises:
            ValueError: 会话不存在。
        """
        if session_id not in self._sessions:
            raise ValueError(f"会话 '{session_id}' 不存在")

        # 取消旧活跃
        if self._active_id and self._active_id in self._sessions:
            self._sessions[self._active_id].is_active = False

        # 设置新活跃
        self._active_id = session_id
        info = self._sessions[session_id]
        info.is_active = True
        return info

    # ── 删除 ────────────────────────────────────────────────

    def delete_session(self, session_id: str) -> bool:
        """删除会话（同时清除历史消息）。

        Args:
            session_id: 目标会话 ID。

        Returns:
            是否成功删除。

        Raises:
            ValueError: 会话不存在。
        """
        if session_id not in self._sessions:
            raise ValueError(f"会话 '{session_id}' 不存在")

        # 清除历史
        self._history_mgr.clear_history(session_id)
        del self._sessions[session_id]

        # 如果删除的是活跃会话，切换到第一个可用
        if self._active_id == session_id:
            remaining = list(self._sessions.keys())
            self._active_id = remaining[0] if remaining else None
            if self._active_id:
                self._sessions[self._active_id].is_active = True

        return True

    # ── 同步 ────────────────────────────────────────────────

    def discover_existing_sessions(self) -> int:
        """从历史记录中发现已有的会话。

        扫描 ChatHistoryManager 中已有的会话并同步到内存。

        Returns:
            发现的会话数量。
        """
        # 通过历史管理器获取已有会话
        # ChatHistoryManager 基于 SQLChatMessageHistory，
        # 需要通过 message_count 探测
        discovered = 0
        # 使用已知的会话 ID 模式进行探测
        known_prefixes = ["cli-chat", "agent-session", "session-"]
        for prefix in known_prefixes:
            for i in range(1, 50):
                sid = (
                    f"{prefix}{i}"
                    if prefix != "cli-chat"
                    else ("cli-chat" if i == 1 else f"cli-chat-{i}")
                )
                try:
                    count = self._history_mgr.message_count(sid)
                    if count > 0 and sid not in self._sessions:
                        info = SessionInfo(
                            session_id=sid,
                            name=sid,
                            message_count=count,
                        )
                        self._sessions[sid] = info
                        discovered += 1
                except Exception:
                    # message_count 可能因表不存在而抛异常
                    break
        return discovered

    def refresh_message_count(self, session_id: str) -> int:
        """刷新指定会话的消息计数。

        Args:
            session_id: 会话 ID。

        Returns:
            更新后的消息数量。
        """
        if session_id not in self._sessions:
            return 0
        count = self._history_mgr.message_count(session_id)
        self._sessions[session_id].message_count = count
        return count

    @property
    def history_manager(self) -> ChatHistoryManager:
        """访问底层历史管理器。"""
        return self._history_mgr
