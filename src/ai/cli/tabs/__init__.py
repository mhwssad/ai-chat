"""Tab 面板抽象基类。"""

import time
from abc import ABC, abstractmethod

from rich.console import Console
from rich.panel import Panel


class BaseTab(ABC):
    """TUI 面板抽象基类。

    所有 Tab 面板（对话、工具、记忆、任务）继承此类，
    实现统一的渲染和事件处理接口。

    Attributes:
        name: Tab 显示名称。
        hotkey: 快捷键标识。
    """

    name: str = "未命名"
    hotkey: str = ""

    def __init__(self) -> None:
        self._selected_index: int = 0
        self._cache_valid: bool = False
        self._cache_time: float = 0.0
        self._cache_ttl: float = 2.0
        self._search_query: str = ""

    @abstractmethod
    def render_content(self, console: Console, width: int, height: int) -> Panel:
        """渲染面板主体内容。

        Args:
            console: Rich Console 实例。
            width: 可用宽度。
            height: 可用高度。

        Returns:
            Rich Panel 对象。
        """
        ...

    @abstractmethod
    def handle_input(self, key: str) -> bool:
        """处理键盘输入。

        Args:
            key: 按键标识（如 "up"、"down"、"enter"、"d" 等）。

        Returns:
            True 表示已处理，False 表示未处理（向上冒泡）。
        """
        ...

    def get_detail_panel(
        self, console: Console, width: int, height: int
    ) -> Panel | None:
        """渲染右侧详情面板（可选）。

        Args:
            console: Rich Console 实例。
            width: 可用宽度。
            height: 可用高度。

        Returns:
            Rich Panel 对象，或 None 表示不显示详情。
        """
        return None

    @abstractmethod
    def _load_data(self) -> None:
        """加载面板数据（子类实现）。

        由 _ensure_cache 在缓存过期时调用。
        """
        ...

    def _invalidate_cache(self) -> None:
        """标记缓存为无效，下次渲染时重新加载数据。"""
        self._cache_valid = False

    def _ensure_cache(self) -> None:
        """确保缓存有效，过期则重新加载。"""
        now = time.monotonic()
        if not self._cache_valid or (now - self._cache_time) >= self._cache_ttl:
            self._load_data()
            self._cache_valid = True
            self._cache_time = now

    def on_activate(self) -> None:
        """Tab 被激活时的回调。"""
        pass

    def on_deactivate(self) -> None:
        """Tab 被取消激活时的回调。"""
        pass

    def set_search_query(self, query: str) -> None:
        """设置搜索关键词，重置选中索引并失效缓存。

        Args:
            query: 搜索关键词。
        """
        self._search_query = query
        self._selected_index = 0
        self._invalidate_cache()

    def clear_search(self) -> None:
        """清除搜索状态。"""
        self._search_query = ""
        self._selected_index = 0
        self._invalidate_cache()

    @property
    def is_searching(self) -> bool:
        """是否处于搜索状态。"""
        return bool(self._search_query)

    def get_footer_commands(self) -> list[tuple[str, str]]:
        """返回底部命令提示列表。

        Returns:
            [(快捷键, 描述), ...] 列表，由子类覆盖。
        """
        return []

    def _move_selection(self, delta: int, item_count: int) -> None:
        """移动选中索引。

        Args:
            delta: 移动方向（+1 向下，-1 向上）。
            item_count: 总项目数。
        """
        if item_count == 0:
            self._selected_index = 0
            return
        self._selected_index = max(0, min(self._selected_index + delta, item_count - 1))

    def _clamp_selection(self, item_count: int) -> None:
        """修正选中索引到合法范围。"""
        if item_count == 0:
            self._selected_index = 0
        else:
            self._selected_index = min(self._selected_index, item_count - 1)

    def _get_scroll_offset(self, visible_count: int, total_count: int) -> int:
        """计算滚动偏移，选中项居中显示。

        Args:
            visible_count: 可见行数。
            total_count: 总项目数。

        Returns:
            起始显示索引。
        """
        if total_count <= visible_count:
            return 0
        # 居中策略：选中项置于可见区域中间
        half = visible_count // 2
        offset = self._selected_index - half
        # 边界修正
        offset = max(0, min(offset, total_count - visible_count))
        return offset


__all__ = ["BaseTab"]
