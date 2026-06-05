"""TUI Tab 抽象与布局元数据。"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from rich.console import Console
from rich.panel import Panel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TabLayoutSpec:
    """Tab 布局偏好。"""

    mode: str = "resource"
    prefer_detail: bool = True
    main_ratio: int = 3
    detail_ratio: int = 2
    min_main_width: int = 60
    min_detail_width: int = 36


@dataclass(frozen=True)
class TabSummary:
    """Tab 统一状态摘要。"""

    title: str
    mode: str
    status: str = ""
    metrics: tuple[tuple[str, str], ...] = ()
    details: tuple[str, ...] = ()


class BaseTab(ABC):
    """TUI 面板抽象基类。"""

    name: str = "未命名"
    hotkey: str = ""
    layout: TabLayoutSpec = TabLayoutSpec()

    def __init__(self, thread_pool: Any) -> None:
        self._thread_pool = thread_pool
        self._selected_index: int = 0
        self._cache_valid: bool = False
        self._cache_time: float = 0.0
        self._cache_ttl: float = 2.0
        self._search_query: str = ""
        self._loading: bool = False
        self._status_setter: Callable[[str], None] | None = None
        self._input_requester: Callable[[str, Callable[[str], None]], None] | None = None
        self._confirm_requester: Callable[[str, Callable[[], None]], None] | None = None
        self._confirm_decision_requester: Callable[
            [str, Callable[[bool], None]], None
        ] | None = None
        self._refresh_requester: Callable[[], None] | None = None

    def bind_ui(
        self,
        *,
        set_status: Callable[[str], None],
        request_input: Callable[[str, Callable[[str], None]], None],
        request_confirm: Callable[[str, Callable[[], None]], None],
        request_confirm_decision: Callable[[str, Callable[[bool], None]], None],
        request_refresh: Callable[[], None],
    ) -> None:
        """绑定 UI 回调。"""
        self._status_setter = set_status
        self._input_requester = request_input
        self._confirm_requester = request_confirm
        self._confirm_decision_requester = request_confirm_decision
        self._refresh_requester = request_refresh

    @abstractmethod
    def render_content(self, console: Console, width: int, height: int) -> Panel:
        """渲染主工作区。"""

    @abstractmethod
    def handle_input(self, key: str) -> bool:
        """处理按键输入。"""

    def get_detail_panel(
        self, console: Console, width: int, height: int
    ) -> Panel | None:
        """渲染检视区。"""
        return None

    def get_tab_header_lines(self) -> list[str]:
        """返回主工作区头部摘要行。"""
        return []

    def get_summary(self) -> TabSummary:
        """返回统一状态摘要，供状态栏、头部和检视区复用。"""
        lines = self.get_tab_header_lines()
        return TabSummary(
            title=self.name,
            mode=self.layout.mode,
            status=lines[0] if lines else "",
            details=tuple(lines[1:]),
        )

    @abstractmethod
    def _load_data(self) -> None:
        """加载面板数据。"""

    def _invalidate_cache(self) -> None:
        self._cache_valid = False

    def _ensure_cache(self) -> None:
        now = time.monotonic()
        if not self._cache_valid or (now - self._cache_time) >= self._cache_ttl:
            if not self._loading:
                self._loading = True
                try:
                    self._thread_pool.run_bg(self._bg_load)
                except Exception:
                    self._loading = False
                    self._load_data()
                    self._cache_valid = True
                    self._cache_time = time.monotonic()

    def _bg_load(self) -> None:
        try:
            self._load_data()
            self._cache_valid = True
            self._cache_time = time.monotonic()
        except Exception as exc:
            logger.debug("后台加载数据失败 (%s): %s", self.name, exc)
        finally:
            self._loading = False
            self._request_refresh()

    def on_activate(self) -> None:
        """Tab 激活回调。"""

    def on_deactivate(self) -> None:
        """Tab 取消激活回调。"""

    def set_search_query(self, query: str) -> None:
        self._search_query = query
        self._selected_index = 0
        self._invalidate_cache()

    def clear_search(self) -> None:
        self._search_query = ""
        self._selected_index = 0
        self._invalidate_cache()

    @property
    def is_searching(self) -> bool:
        return bool(self._search_query)

    def get_footer_commands(self) -> list[tuple[str, str]]:
        return []

    def register_commands(self, router: Any, tab_index: int) -> None:
        """向命令路由器注册 Tab 私有命令。"""
        return None

    def _move_selection(self, delta: int, item_count: int) -> None:
        if item_count == 0:
            self._selected_index = 0
            return
        self._selected_index = max(0, min(self._selected_index + delta, item_count - 1))

    def _clamp_selection(self, item_count: int) -> None:
        if item_count == 0:
            self._selected_index = 0
        else:
            self._selected_index = min(self._selected_index, item_count - 1)

    def _get_scroll_offset(self, visible_count: int, total_count: int) -> int:
        if total_count <= visible_count:
            return 0
        half = visible_count // 2
        offset = self._selected_index - half
        return max(0, min(offset, total_count - visible_count))

    def _set_status(self, message: str) -> None:
        if self._status_setter is not None:
            self._status_setter(message)

    def _request_input(self, prompt: str, callback: Callable[[str], None]) -> None:
        if self._input_requester is not None:
            self._input_requester(prompt, callback)

    def _request_confirm(self, message: str, action: Callable[[], None]) -> None:
        if self._confirm_requester is not None:
            self._confirm_requester(message, action)

    def _request_confirm_decision(
        self, message: str, callback: Callable[[bool], None]
    ) -> None:
        if self._confirm_decision_requester is not None:
            self._confirm_decision_requester(message, callback)
            return
        callback(False)

    def _request_refresh(self) -> None:
        if self._refresh_requester is not None:
            self._refresh_requester()


__all__ = ["BaseTab", "TabLayoutSpec", "TabSummary"]
