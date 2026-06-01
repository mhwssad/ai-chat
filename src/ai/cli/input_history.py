"""输入历史管理 — 支持上下翻阅历史输入。"""


class InputHistory:
    """输入历史管理器。

    支持上下翻阅历史输入记录，最大 100 条，自动去重。

    Usage:
        history = InputHistory()
        history.add("hello")
        history.add("world")
        history.prev()  # "world"
        history.prev()  # "hello"
        history.next()  # "world"
    """

    def __init__(self, max_size: int = 100) -> None:
        self._items: list[str] = []
        self._max_size = max_size
        self._cursor: int = -1  # -1 表示未在历史中导航

    def add(self, text: str) -> None:
        """添加输入到历史记录（自动去重）。

        Args:
            text: 输入文本。
        """
        text = text.strip()
        if not text:
            return
        # 去重：如果已存在，移到末尾
        if text in self._items:
            self._items.remove(text)
        self._items.append(text)
        # 超出容量时移除最旧的
        if len(self._items) > self._max_size:
            self._items = self._items[-self._max_size :]
        self._cursor = -1

    def prev(self) -> str | None:
        """获取上一条历史记录。

        Returns:
            历史文本，或 None（已到最早记录）。
        """
        if not self._items:
            return None
        if self._cursor == -1:
            self._cursor = len(self._items) - 1
        elif self._cursor > 0:
            self._cursor -= 1
        return self._items[self._cursor]

    def next(self) -> str | None:
        """获取下一条历史记录。

        Returns:
            历史文本，或 None（已到最新记录）。
        """
        if not self._items or self._cursor == -1:
            return None
        if self._cursor < len(self._items) - 1:
            self._cursor += 1
            return self._items[self._cursor]
        # 已到末尾，重置
        self._cursor = -1
        return None

    def reset(self) -> None:
        """重置导航位置（不清除历史）。"""
        self._cursor = -1

    @property
    def count(self) -> int:
        """历史记录条数。"""
        return len(self._items)
